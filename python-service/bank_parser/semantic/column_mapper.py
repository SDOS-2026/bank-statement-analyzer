import re
import pandas as pd
from rapidfuzz import fuzz
from typing import Dict, Optional

STANDARD_SCHEMA = ["Date", "Description", "Debit", "Credit", "Balance", "Reference"]

COLUMN_ALIASES = {
    "Date": [
        "date", "txn date", "value date", "trans date", "transaction date",
        "posting date", "dt", "value dt", "transaction\ndate", "post date",
        "posted date", "tran date", "entry date",
    ],
    "Description": [
        "description", "narration", "description/narration", "particulars",
        "remarks", "transaction details", "details", "narrative",
        "trans particulars", "description narration", "transaction remarks",
    ],
    "Debit": [
        "debit", "dr", "withdrawal", "withdrawals", "paid out",
        "debit amount", "withdrawal amount", "debit (rs)", "debit (inr)",
        "debit(rs)", "debit(inr)", "dr amount", "withdrawal (dr)",
        "withdrawal dr", "amount (dr)",
    ],
    "Credit": [
        "credit", "cr", "deposit", "deposits", "paid in",
        "credit amount", "deposit amount", "credit (rs)", "credit (inr)",
        "credit(rs)", "credit(inr)", "cr amount", "deposit (cr)",
        "deposit cr", "amount (cr)",
    ],
    "Balance": [
        "balance", "running balance", "available balance", "closing balance",
        "avl bal", "closing bal", "bal", "balance (rs)", "balance (inr)",
        "balance(rs)", "balance(inr)", "running bal", "book balance",
    ],
    "Reference": [
        "ref no", "reference", "cheque no", "chq no", "instrument no",
        "utr", "ref", "chq/ref no", "cheque/reference no",
        "cheque/ reference no.", "cheque reference no", "instrument id",
        "chq / ref no.",
    ],
    # Detect the combined amount column
    "Amount": [
        "amount", "amt", "amount (inr)", "amount(inr)", "amount (rs)",
        "amount(rs)", "amount (rs.)", "amount(rs.)", "transaction amount", "txn amount",
        "withdrawal/deposit", "dr/cr amount", "amount dr/cr",
    ],
    # Detect the DR/CR type column
    "TxnType": [
        "type", "dr/cr", "cr/dr", "txn type", "transaction type",
        "debit/credit", "credit/debit", "flag", "dc", "d/c",
    ],
}


def _clean_col_name(col: str) -> str:
    """Strip currency symbols, brackets, extra spaces for matching."""
    col = str(col).lower().strip()
    col = re.sub(r'[₹\(\)\[\]]', '', col)
    col = re.sub(r'\s+', ' ', col).strip()
    return col


def map_columns(raw_columns: list) -> Dict[str, str]:
    """
    Map raw column names → standard names using fuzzy matching.
    Returns {raw_col → standard_col}.
    """
    mapping = {}
    used_standards = set()

    for raw_col in raw_columns:
        cleaned = _clean_col_name(raw_col)

        # Prevent common false matches: headers like "post"/"value" should map to Date.
        if 'date' in cleaned or cleaned in {'post', 'value', 'post dt', 'value dt'}:
            if 'Date' not in used_standards:
                mapping[raw_col] = 'Date'
                used_standards.add('Date')
                continue

        best_std = None
        best_score = 0

        for std_col, aliases in COLUMN_ALIASES.items():
            if std_col in used_standards:
                continue

            # Never infer Date from identifier-like headers.
            if std_col == 'Date' and ('id' in cleaned and 'date' not in cleaned):
                continue

            for alias in aliases:
                score = fuzz.token_sort_ratio(cleaned, alias)
                threshold = 65
                if len(cleaned) <= 4 and std_col != 'Date':
                    threshold = 82
                if std_col == 'Date' and 'date' not in cleaned and cleaned not in {'post', 'value', 'dt', 'tran date', 'txn date', 'post dt', 'value dt'}:
                    threshold = 88
                if score > best_score and score > threshold:
                    best_score = score
                    best_std = std_col

        if best_std:
            mapping[raw_col] = best_std
            used_standards.add(best_std)

    return mapping


def _parse_amount(val) -> Optional[float]:
    if val is None:
        return None
    s = str(val).strip()
    if s in ('', '-', '--', 'nan', 'None'):
        return None
    # Handle directional wrappers: 300.00 (Dr), 300.00DR, DR 300.00
    s = s.upper()
    s = s.replace('(', ' ').replace(')', ' ')
    s = re.sub(r'\b(?:DR|CR|DEBIT|CREDIT)\b', '', s)
    s = re.sub(r'[₹,\s]', '', s)
    try:
        v = float(s)
        return v
    except ValueError:
        return None


def _parse_amount_with_direction(val) -> tuple[Optional[float], Optional[str]]:
    if val is None:
        return None, None
    raw = str(val).strip()
    if raw in ('', '-', '--', 'nan', 'None'):
        return None, None

    upper = raw.upper()
    direction = None
    if re.search(r'\bDR\b|\(DR\)', upper):
        direction = 'DR'
    elif re.search(r'\bCR\b|\(CR\)', upper):
        direction = 'CR'

    return _parse_amount(raw), direction


def _split_combined_amount(df: pd.DataFrame) -> pd.DataFrame:
    """
    Handle PNB / IOB / some SBI style:
      One 'Amount' column + one 'TxnType' column with values DR/CR.

    Splits into separate Debit and Credit columns.
    """
    if 'Amount' not in df.columns or 'TxnType' not in df.columns:
        return df

    print("[ColumnMapper] Detected combined Amount+TxnType pattern — splitting into Debit/Credit")

    def to_debit(row):
        t = str(row.get('TxnType', '')).strip().upper()
        if t in ('DR', 'D', 'DEBIT', 'WDL', 'WITHDRAWAL'):
            return _parse_amount(row.get('Amount'))
        return None

    def to_credit(row):
        t = str(row.get('TxnType', '')).strip().upper()
        if t in ('CR', 'C', 'CREDIT', 'DEP', 'DEPOSIT'):
            return _parse_amount(row.get('Amount'))
        return None

    df = df.copy()
    df['Debit']  = df.apply(to_debit,  axis=1)
    df['Credit'] = df.apply(to_credit, axis=1)
    df.drop(columns=['Amount', 'TxnType'], inplace=True, errors='ignore')
    return df


def _split_directional_amount(df: pd.DataFrame) -> pd.DataFrame:
    """
    Handle single amount column with inline direction markers:
    - 300.00 (Dr)
    - 10,000.00 CR
    """
    if 'Amount' not in df.columns:
        return df

    if 'Debit' in df.columns and 'Credit' in df.columns:
        return df

    print("[ColumnMapper] Detected single Amount column with inline direction — splitting")
    df = df.copy()

    def to_debit(v):
        amount, direction = _parse_amount_with_direction(v)
        return amount if direction == 'DR' else None

    def to_credit(v):
        amount, direction = _parse_amount_with_direction(v)
        return amount if direction == 'CR' else None

    df['Debit'] = df['Amount'].apply(to_debit)
    df['Credit'] = df['Amount'].apply(to_credit)

    unresolved = df['Debit'].isna() & df['Credit'].isna()
    if unresolved.any():
        # No direction marker present; treat as debit by default (common in statements)
        df.loc[unresolved, 'Debit'] = df.loc[unresolved, 'Amount'].apply(_parse_amount)

    df.drop(columns=['Amount'], inplace=True, errors='ignore')
    return df


def apply_column_mapping(df: pd.DataFrame, bank_overrides: dict = None) -> pd.DataFrame:
    bank_overrides = bank_overrides or {}

    mapping = map_columns(df.columns.tolist())
    print(f"[ColumnMapper] Mapping: {mapping}")
    df = df.rename(columns=mapping)
    df = df.loc[:, ~df.columns.duplicated()]

    # Backfill Date mapping from column values when headers are ambiguous.
    df = _infer_missing_date_column(df)

    # ── Case 1: Combined Amount + TxnType (PNB / IOB / Allahabad) ────────────
    df = _split_combined_amount(df)

    # ── Case 1b: Single Amount column with embedded DR/CR ────────────────────
    df = _split_directional_amount(df)

    # ── Case 2: Still no Debit/Credit — try Amount + inline DR/CR in value ───
    # Some banks put "500 DR" or "200 CR" directly in the amount cell
    if 'Debit' not in df.columns and 'Credit' not in df.columns:
        if 'Amount' in df.columns:
            print("[ColumnMapper] Trying inline DR/CR amount parsing")
            df['Debit']  = df['Amount'].apply(lambda v: _inline_amount(v, 'DR'))
            df['Credit'] = df['Amount'].apply(lambda v: _inline_amount(v, 'CR'))
            df.drop(columns=['Amount'], inplace=True, errors='ignore')

    # ── Ensure all standard columns exist ────────────────────────────────────
    for col in STANDARD_SCHEMA:
        if col not in df.columns:
            df[col] = None

    # Drop any extra non-standard columns (like TxnType if not yet dropped)
    keep = [c for c in STANDARD_SCHEMA if c in df.columns]
    return df[keep].copy()


def _inline_amount(val, direction: str) -> Optional[float]:
    """
    Parse values like '500 DR', '200CR', '1,234.56 CR'.
    Returns the number only if direction matches.
    """
    s = str(val).strip().upper()
    # Detect direction marker at end
    has_dr = bool(re.search(r'\bDR\b|\(DR\)|D$', s))
    has_cr = bool(re.search(r'\bCR\b|\(CR\)|C$', s))
    if not has_dr and not has_cr:
        return None
    # Strip the marker and parse
    s = re.sub(r'\b(?:DR|CR|DEBIT|CREDIT)\b', '', s).replace('(', ' ').replace(')', ' ').strip()
    s = re.sub(r'[₹,\s]', '', s)
    try:
        v = float(s)
        if direction == 'DR' and has_dr:
            return v
        if direction == 'CR' and has_cr:
            return v
        return None
    except ValueError:
        return None


def _date_like_ratio(series: pd.Series) -> float:
    s = series.astype(str).str.strip()
    if len(s) == 0:
        return 0.0
    pattern = r'(^\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}$)|(^\d{1,2}\s+[A-Za-z]{3,9}(\s+\d{2,4})?$)'
    return float(s.str.contains(pattern, regex=True, na=False).mean())


def _infer_missing_date_column(df: pd.DataFrame) -> pd.DataFrame:
    if 'Date' in df.columns and df['Date'].notna().any():
        return df

    candidates = [c for c in df.columns if c not in STANDARD_SCHEMA]
    best_col = None
    best_ratio = 0.0

    for c in candidates:
        ratio = _date_like_ratio(df[c])
        if ratio > best_ratio:
            best_ratio = ratio
            best_col = c

    if best_col and best_ratio >= 0.45:
        print(f"[ColumnMapper] Inferred Date column from values: {best_col} (ratio={best_ratio:.2f})")
        df['Date'] = df[best_col]

    return df


# ── Balance CR/DR suffix cleaner (called from reconstructor) ─────────────────
# Allahabad Bank: "15,234.50 CR" or "500.00 DR"

def clean_balance_cr_dr(val) -> Optional[float]:
    """
    Parse balance values that have CR/DR suffix.
    '15,234.50 CR' → 15234.50
    '500.00 DR'    → -500.00  (negative balance, rare but handle it)
    Regular '15234.50' → 15234.50
    """
    if val is None:
        return None
    s = str(val).strip().upper()
    if s in ('', '-', 'NAN', 'NONE', 'NAT'):
        return None

    # Check for CR/DR suffix
    has_dr = bool(re.search(r'\bDR\b$', s))
    has_cr = bool(re.search(r'\bCR\b$', s))

    # Strip all non-numeric except dot and minus
    num_str = re.sub(r'[A-Z₹,\s]', '', s)
    try:
        v = float(num_str)
        if has_dr and v > 0:
            return -v   # DR balance = overdrawn = negative
        return v if v != 0 else None
    except ValueError:
        return None
