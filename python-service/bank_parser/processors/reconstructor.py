import re
import pandas as pd
from typing import Optional
from semantic.column_mapper import clean_balance_cr_dr

DATE_FORMATS = [
    "%d %b %Y",    # 01 Feb 2026  (AU, SBI)
    "%d-%b-%Y",    # 01-Feb-2026
    "%d/%m/%Y",    # 01/02/2026   (HDFC, ICICI)
    "%d-%m-%Y",    # 01-02-2026
    "%d.%m.%Y",    # 01.02.2026
    "%d/%m/%y",    # 01/02/26
    "%d-%m-%y",    # 01-02-26
    "%Y-%m-%d",    # 2026-02-01   (ISO)
    "%d %B %Y",    # 01 February 2026
    "%d/%b/%Y",    # 01/Feb/2026
]

DATE_WORD_RE = re.compile(
    r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}\b',
    re.IGNORECASE
)
DATE_NUM_RE = re.compile(r'\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b')


def _is_empty(val) -> bool:
    return pd.isna(val) or str(val).strip().lower() in ('', 'nan', 'none', '-', '--', 'nat')


def _parse_amount(val) -> Optional[float]:
    """Parse numeric amount — strips commas, ₹, handles None/-."""
    if _is_empty(val):
        return None
    s = str(val).strip()
    s = re.sub(r'[₹,\s]', '', s)
    # Strip any trailing DR/CR that wasn't caught earlier
    s = re.sub(r'(?i)(cr|dr)$', '', s).strip()
    try:
        v = float(s)
        return v if v != 0.0 else None
    except ValueError:
        return None


def _parse_date(val) -> pd.Timestamp:
    if _is_empty(val):
        return pd.NaT
    s = re.sub(r'\s+', ' ', str(val).strip())
    for fmt in DATE_FORMATS:
        try:
            return pd.to_datetime(s, format=fmt)
        except Exception:
            continue
    try:
        return pd.to_datetime(s, dayfirst=True)
    except Exception:
        return pd.NaT


def _has_date(val) -> bool:
    s = str(val).strip()
    return bool(DATE_WORD_RE.search(s)) or bool(DATE_NUM_RE.search(s))


# ── Reconstruction steps ──────────────────────────────────────────────────────

def fix_date_grouping(df: pd.DataFrame) -> pd.DataFrame:
    """Handle statements where a single date row precedes multiple transactions."""
    current_date = None
    rows_to_drop = []

    for i, row in df.iterrows():
        date_val = row.get('Date', '')
        has_amounts = not (
            _is_empty(row.get('Debit', '')) and
            _is_empty(row.get('Credit', '')) and
            _is_empty(row.get('Balance', ''))
        )

        if _has_date(str(date_val)) and not has_amounts:
            current_date = str(date_val).strip()
            rows_to_drop.append(i)
        elif _is_empty(date_val) and current_date:
            df.at[i, 'Date'] = current_date

    df.drop(index=rows_to_drop, inplace=True)
    return df.reset_index(drop=True)


def forward_fill_dates(df: pd.DataFrame) -> pd.DataFrame:
    df['Date'] = df['Date'].replace('', pd.NA).replace('None', pd.NA)
    df['Date'] = df['Date'].ffill()
    return df


def merge_multiline_descriptions(df: pd.DataFrame) -> pd.DataFrame:
    rows_to_drop = []
    idx_list = df.index.tolist()

    for pos in range(1, len(idx_list)):
        curr_i = idx_list[pos]
        prev_i = idx_list[pos - 1]
        row = df.loc[curr_i]

        if (
            _is_empty(row.get('Date', '')) and
            _is_empty(row.get('Debit', '')) and
            _is_empty(row.get('Credit', '')) and
            _is_empty(row.get('Balance', '')) and
            not _is_empty(row.get('Description', ''))
        ):
            prev_desc = str(df.at[prev_i, 'Description'])
            cont_desc = str(row.get('Description', ''))
            df.at[prev_i, 'Description'] = f"{prev_desc} {cont_desc}".strip()
            rows_to_drop.append(curr_i)

    df.drop(index=rows_to_drop, inplace=True)
    return df.reset_index(drop=True)


def clean_descriptions(df: pd.DataFrame) -> pd.DataFrame:
    for col in ['Description', 'Reference']:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(r'\n+', ' ', regex=True)
                .str.replace(r'\s+', ' ', regex=True)
                .str.strip()
                .replace('nan', None)
                .replace('None', None)
            )
    return df


def clean_amounts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean Debit and Credit with standard parser.
    Clean Balance with CR/DR-aware parser (handles Allahabad Bank format).
    """
    for col in ['Debit', 'Credit']:
        if col in df.columns:
            df[col] = df[col].apply(_parse_amount)

    if 'Balance' in df.columns:
        # Use CR/DR-aware cleaner for Balance column
        df['Balance'] = df['Balance'].apply(clean_balance_cr_dr)

    return df


def clean_dates(df: pd.DataFrame) -> pd.DataFrame:
    if 'Date' in df.columns:
        df['Date'] = df['Date'].apply(_parse_date)
    return df


def reconstruct(df: pd.DataFrame) -> pd.DataFrame:
    df = fix_date_grouping(df)
    df = forward_fill_dates(df)
    df = merge_multiline_descriptions(df)
    df = clean_descriptions(df)
    df = clean_amounts(df)
    df = clean_dates(df)
    df = df.dropna(subset=['Date'])
    return df.reset_index(drop=True)
