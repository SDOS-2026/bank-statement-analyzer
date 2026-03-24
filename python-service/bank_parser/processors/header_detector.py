import re
import pandas as pd
from typing import Tuple

DATE_PATTERN = re.compile(
    r'\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b'       # 01/02/2024
    r'|\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b',  # 01 Feb 2026
    re.IGNORECASE
)
AMOUNT_PATTERN = re.compile(r'\b\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?\b')

HEADER_KEYWORDS = {
    'date':        ['date', 'txn date', 'value date', 'transaction date', 'trans date'],
    'description': ['description', 'narration', 'particulars', 'remarks',
                    'transaction details', 'details'],
    'debit':       ['debit', 'dr', 'withdrawal', 'withdrawals', 'paid out'],
    'credit':      ['credit', 'cr', 'deposit', 'deposits', 'paid in'],
    'balance':     ['balance', 'running balance', 'closing balance', 'avl balance'],
    'reference':   ['ref', 'reference', 'cheque', 'chq', 'instrument'],
}


def _flatten(val: str) -> str:
    """Replace newlines and extra spaces inside a cell value."""
    return re.sub(r'\s+', ' ', str(val).replace('\n', ' ')).strip().lower()


def find_header_row(df: pd.DataFrame) -> int:
    """
    Scan each row, score it by how many header keywords it contains.
    The row with the highest score is the header.
    Returns row index (integer position, not label).
    """
    best_row = 0
    best_score = -1

    for i in range(min(len(df), 10)):   # Header can't be beyond row 10
        row_text = ' '.join(_flatten(v) for v in df.iloc[i].values)
        score = sum(
            1 for keywords in HEADER_KEYWORDS.values()
            for kw in keywords if kw in row_text
        )
        if score > best_score:
            best_score = score
            best_row = i

    return best_row if best_score >= 2 else 0


def _is_data_row(row: pd.Series) -> bool:
    """A data row must have at least one date or one amount."""
    text = ' '.join(str(v) for v in row.values)
    return bool(DATE_PATTERN.search(text)) or bool(AMOUNT_PATTERN.search(text))


def split_header_and_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, list]:
    """
    1. Find header row
    2. Use it to set column names (flattening internal newlines)
    3. Drop non-data rows (sub-headers, totals, blank lines)
    Returns (clean_df, raw_column_names)
    """
    header_idx = find_header_row(df)

    # Flatten newlines in header cells: 'Transaction\nDate' → 'Transaction Date'
    raw_cols = [_flatten(v) for v in df.iloc[header_idx].values]
    df = df.iloc[header_idx + 1:].copy()
    df.columns = raw_cols

    # Drop rows that contain repeated headers (common on each page)
    def is_header_repeat(row):
        text = ' '.join(str(v).lower() for v in row.values)
        score = sum(
            1 for keywords in HEADER_KEYWORDS.values()
            for kw in keywords if kw in text
        )
        return score >= 3   # Looks like another header row

    df = df[~df.apply(is_header_repeat, axis=1)]

    # Drop rows that are clearly footers/totals
    footer_re = re.compile(r'\b(total|grand total|opening balance|closing balance|page \d)\b', re.I)
    df = df[~df.apply(
        lambda row: bool(footer_re.search(' '.join(str(v) for v in row.values))),
        axis=1
    )]

    # Keep only rows with actual transaction data
    df = df[df.apply(_is_data_row, axis=1)]

    return df.reset_index(drop=True), raw_cols
