"""
extractor/excel_engine.py

Handles extraction from spreadsheet formats:
  - .xlsx  (OpenPyXL)
  - .xls   (xlrd)
  - .ods   (odfpy)

Supports:
  - Password-protected .xlsx (via msoffcrypto-tool)
  - Multiple sheets (picks best scoring one)
  - Header row auto-detection
  - Returns same ExtractionResult as pdf engine_runner
"""

import re
import io
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import pandas as pd

# Scoring (same logic as PDF engine)
DATE_RE   = re.compile(r'\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b|\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}\b', re.I)
AMOUNT_RE = re.compile(r'\b\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?\b')

HEADER_KEYWORDS = [
    'date', 'debit', 'credit', 'balance', 'narration', 'particulars',
    'withdrawal', 'deposit', 'amount', 'description', 'cheque', 'value',
    'reference', 'remarks', 'transaction',
]


@dataclass
class SpreadsheetExtractionResult:
    tables: List[pd.DataFrame]
    engine: str
    confidence: float
    page_coverage: float
    encrypted: bool = False


def score_table(df: pd.DataFrame) -> float:
    if df is None or df.empty or len(df.columns) < 3 or len(df) < 2:
        return 0.0

    score = 0.0
    full_text = df.to_string().lower()

    if DATE_RE.search(full_text):
        score += 0.35

    numeric_cols = 0
    for col in df.columns:
        vals = df[col].astype(str).str.replace(r'[,₹\s]', '', regex=True)
        valid = vals.apply(lambda v: bool(re.match(r'^-?\d+\.?\d*$', v)) or v == '-')
        if valid.mean() > 0.4:
            numeric_cols += 1
    if numeric_cols >= 2:
        score += 0.35
    elif numeric_cols == 1:
        score += 0.15

    header_text = ' '.join(str(v) for v in list(df.columns) + list(df.iloc[0].values)).lower()
    hits = sum(1 for kw in HEADER_KEYWORDS if kw in header_text)
    score += min(hits * 0.05, 0.30)

    return round(min(score, 1.0), 3)


def _find_header_row(df: pd.DataFrame) -> int:
    """Find the row index that looks like a column header."""
    best_i, best_score = 0, -1
    for i in range(min(len(df), 15)):
        row_text = ' '.join(str(v) for v in df.iloc[i].values).lower()
        hits = sum(1 for kw in HEADER_KEYWORDS if kw in row_text)
        if hits > best_score:
            best_score = hits
            best_i = i
    return best_i if best_score >= 2 else 0


def _promote_header(df: pd.DataFrame) -> pd.DataFrame:
    """Make the best header row into column names."""
    header_idx = _find_header_row(df)
    df.columns = [str(v).strip() for v in df.iloc[header_idx].values]
    df = df.iloc[header_idx + 1:].reset_index(drop=True)
    # Drop all-empty rows
    df = df.dropna(how='all')
    df = df[~df.apply(lambda r: all(str(v).strip() in ('', 'nan', 'None') for v in r), axis=1)]
    return df.reset_index(drop=True)


# ── Format-specific readers ───────────────────────────────────────────────────

def read_xlsx(path: str, password: Optional[str] = None) -> Tuple[List[pd.DataFrame], bool]:
    """Read .xlsx, optionally decrypting with password first."""
    is_encrypted = False

    if password:
        try:
            import msoffcrypto
            with open(path, 'rb') as f:
                office_file = msoffcrypto.OfficeFile(f)
                if office_file.is_encrypted():
                    is_encrypted = True
                    decrypted = io.BytesIO()
                    office_file.load_key(password=password)
                    office_file.decrypt(decrypted)
                    decrypted.seek(0)
                    xl = pd.ExcelFile(decrypted, engine='openpyxl')
                else:
                    xl = pd.ExcelFile(path, engine='openpyxl')
        except ImportError:
            print("[Excel] msoffcrypto not installed — trying without password decryption")
            xl = pd.ExcelFile(path, engine='openpyxl')
        except Exception as e:
            raise RuntimeError(f"Failed to decrypt .xlsx: {e}")
    else:
        try:
            xl = pd.ExcelFile(path, engine='openpyxl')
        except Exception as e:
            # May be encrypted
            if 'encrypted' in str(e).lower() or 'password' in str(e).lower():
                return [], True
            raise

    sheets = []
    for sheet_name in xl.sheet_names:
        try:
            raw = xl.parse(sheet_name, header=None, dtype=str)
            raw = raw.dropna(how='all').reset_index(drop=True)
            if len(raw) > 2:
                df = _promote_header(raw)
                if score_table(df) > 0.2:
                    sheets.append(df)
        except Exception as e:
            print(f"[Excel] Sheet '{sheet_name}' failed: {e}")

    return sheets, is_encrypted


def read_xls(path: str) -> List[pd.DataFrame]:
    """Read legacy .xls format."""
    try:
        xl = pd.ExcelFile(path, engine='xlrd')
    except Exception as e:
        raise RuntimeError(f"Failed to open .xls: {e}")

    sheets = []
    for name in xl.sheet_names:
        try:
            raw = xl.parse(name, header=None, dtype=str)
            raw = raw.dropna(how='all').reset_index(drop=True)
            if len(raw) > 2:
                df = _promote_header(raw)
                if score_table(df) > 0.2:
                    sheets.append(df)
        except Exception as e:
            print(f"[Excel] Sheet '{name}' failed: {e}")

    return sheets


def read_ods(path: str) -> List[pd.DataFrame]:
    """Read OpenDocument Spreadsheet .ods format."""
    try:
        import odf.opendocument
        xl = pd.ExcelFile(path, engine='odf')
    except Exception as e:
        raise RuntimeError(f"Failed to open .ods: {e}")

    sheets = []
    for name in xl.sheet_names:
        try:
            raw = xl.parse(name, header=None, dtype=str)
            raw = raw.dropna(how='all').reset_index(drop=True)
            if len(raw) > 2:
                df = _promote_header(raw)
                if score_table(df) > 0.2:
                    sheets.append(df)
        except Exception as e:
            print(f"[Excel] ODS Sheet '{name}' failed: {e}")

    return sheets


# Public API

def is_spreadsheet(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    return ext in ('.xlsx', '.xls', '.ods', '.csv')


def check_spreadsheet_encrypted(path: str) -> bool:
    """Returns True if the spreadsheet requires a password."""
    ext = os.path.splitext(path)[1].lower()
    if ext != '.xlsx':
        return False  # Only xlsx supports encryption commonly
    try:
        import msoffcrypto
        with open(path, 'rb') as f:
            return msoffcrypto.OfficeFile(f).is_encrypted()
    except ImportError:
        # Try opening — if it fails with encryption error, it's encrypted
        try:
            pd.ExcelFile(path, engine='openpyxl')
            return False
        except Exception as e:
            return 'encrypted' in str(e).lower() or 'password' in str(e).lower()
    except Exception:
        return False


def extract_spreadsheet(
    path: str,
    password: Optional[str] = None
) -> SpreadsheetExtractionResult:
    """
    Main entry point for spreadsheet extraction.
    Returns SpreadsheetExtractionResult compatible with the PDF pipeline.
    """
    ext = os.path.splitext(path)[1].lower()
    print(f"[Excel] Extracting {ext} file: {path}", flush=True)

    try:
        if ext == '.xlsx':
            tables, encrypted = read_xlsx(path, password)
            if encrypted and not password:
                return SpreadsheetExtractionResult([], 'excel_xlsx', 0.0, 0.0, encrypted=True)
            engine = 'excel_xlsx'

        elif ext == '.xls':
            tables = read_xls(path)
            encrypted = False
            engine = 'excel_xls'

        elif ext == '.ods':
            tables = read_ods(path)
            encrypted = False
            engine = 'excel_ods'

        elif ext == '.csv':
            df = pd.read_csv(path, dtype=str, on_bad_lines='skip')
            df = _promote_header(df) if score_table(df) < 0.3 else df
            tables = [df] if score_table(df) > 0.2 else []
            encrypted = False
            engine = 'csv'

        else:
            raise ValueError(f"Unsupported spreadsheet format: {ext}")

        if not tables:
            return SpreadsheetExtractionResult([], engine, 0.0, 0.0)

        scores = [score_table(t) for t in tables]
        avg_conf = sum(scores) / len(scores)

        print(f"[Excel] {len(tables)} sheet(s), avg confidence: {avg_conf:.3f}", flush=True)
        return SpreadsheetExtractionResult(tables, engine, avg_conf, 1.0)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return SpreadsheetExtractionResult([], f'excel_{ext}', 0.0, 0.0)


## testing