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
        "debit(rs)", "debit(inr)", "dr amount",
    ],
    "Credit": [
        "credit", "cr", "deposit", "deposits", "paid in",
        "credit amount", "deposit amount", "credit (rs)", "credit (inr)",
        "credit(rs)", "credit(inr)", "cr amount",
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
        "chq / ref no.", "transaction id", "txn id",
    ],
    # Detect the combined amount column
    "Amount": [
        "amount", "amt", "amount (inr)", "amount(inr)", "amount (rs)",
        "amount(rs)", "transaction amount", "txn amount",
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
        best_std = None
        best_score = 0

        for std_col, aliases in COLUMN_ALIASES.items():
            if std_col in used_standards:
                continue
            for alias in aliases:
                score = fuzz.token_sort_ratio(cleaned, alias)
                if score > best_score and score > 65:
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
    s = re.sub(r'[₹,\s]', '', s)
    try:
        v = float(s)
        return v if v != 0.0 else None
    except ValueError:
        return None


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


def apply_column_mapping(df: pd.DataFrame, bank_overrides: dict = None) -> pd.DataFrame:
    bank_overrides = bank_overrides or {}

    mapping = map_columns(df.columns.tolist())
    print(f"[ColumnMapper] Mapping: {mapping}")
    df = df.rename(columns=mapping)

    # ── Case 1: Combined Amount + TxnType (PNB / IOB / Allahabad) ────────────
    df = _split_combined_amount(df)

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
    has_dr = s.endswith('DR') or s.endswith('D')
    has_cr = s.endswith('CR') or s.endswith('C')
    if not has_dr and not has_cr:
        return None
    # Strip the marker and parse
    s = re.sub(r'[A-Z]+$', '', s).strip()
    s = re.sub(r'[₹,\s]', '', s)
    try:
        v = float(s)
        if direction == 'DR' and has_dr:
            return v if v != 0 else None
        if direction == 'CR' and has_cr:
            return v if v != 0 else None
        return None
    except ValueError:
        return None


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
