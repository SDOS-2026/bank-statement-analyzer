"""
Multi-engine PDF table extractor with confidence scoring.

Key fixes vs v1:
- score_table handles '-' as empty amounts (AU Bank, HDFC style)
- Tries pdfplumber with both 'lines' and 'lines_strict' strategies
- Properly scores tables even when debit/credit are dashes
"""

import re
import pdfplumber 
import fitz
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# pdf plumber and PyPDF(fitz) being used for data extraction

DATE_PATTERN = re.compile(r'\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b')
DATE_WORD_PATTERN = re.compile(
    r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b',
    re.IGNORECASE
)
DATE_WORD_SHORT_PATTERN = re.compile(
    r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b',
    re.IGNORECASE
)
FULL_DATE_SEARCH_PATTERN = re.compile(
    r'\b(?:\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[A-Za-z]*\s+\d{2,4})\b',
    re.IGNORECASE
)
# Matches numbers including Indian comma-formatted ones, optionally preceded by -/₹
AMOUNT_PATTERN = re.compile(r'\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})')
TXN_START_PATTERN = re.compile(
    r'^\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,9}(?:\s+\d{2,4})?|\d{1,2})\b',
    re.IGNORECASE
)
DR_CR_PATTERN = re.compile(r'\b(?:DR|CR)\b|\((?:DR|CR)\)', re.IGNORECASE)
PLUS_MINUS_RS_PATTERN = re.compile(r'([+-])\s*Rs\.?\s*([\d,]+(?:\.\d{1,2})?)', re.IGNORECASE)


# headers of the data extracted from the bank statement

HEADER_KEYWORDS = [
    'date', 'debit', 'credit', 'balance', 'narration',
    'particulars', 'withdrawal', 'deposit', 'amount',
    'description', 'cheque', 'reference', 'value'
]


@dataclass
class ExtractionResult:
    tables: List[pd.DataFrame]
    engine: str
    confidence: float
    page_coverage: float


def score_table(df: pd.DataFrame) -> float:
    """
    Score a candidate table 0.0–1.0.

    Fixes:
    - AU Bank uses '-' for empty Debit/Credit → still valid
    - Dates may be written as '01 Feb 2026' (word month) not just '01/02/2026'
    - Header keywords count as strong signal
    """
    if df is None or df.empty:
        return 0.0
    if len(df.columns) < 3 or len(df) < 2:
        return 0.0

    score = 0.0
    full_text = df.fillna('').astype(str).to_string().lower()

    # --- Date detection (numeric or word month) ---
    if DATE_PATTERN.search(full_text) or DATE_WORD_PATTERN.search(full_text) or DATE_WORD_SHORT_PATTERN.search(full_text):
        score += 0.35

    # --- Numeric amount detection ---
    # Count cells that are pure amounts (or '-' which means zero)
    numeric_cols = 0
    for col in df.columns:
        col_vals = df[col].astype(str).str.strip()
        # A column is "numeric" if >50% of values are amounts or dashes
        valid = col_vals.apply(
            lambda v: bool(AMOUNT_PATTERN.search(v)) or v in ('-', '--')
        )
        if valid.mean() > 0.5:
            numeric_cols += 1

    if numeric_cols >= 2:
        score += 0.35
    elif numeric_cols == 1:
        score += 0.15

    # --- Header keyword detection (check first 2 rows and column names) ---
    header_text = ' '.join(
        str(v).lower()
        for v in list(df.columns) + list(df.iloc[0].values if len(df) > 0 else [])
    )
    # Flatten newlines in headers (AU Bank has 'Transaction\nDate')
    header_text = header_text.replace('\n', ' ')
    hits = sum(1 for kw in HEADER_KEYWORDS if kw in header_text)
    score += min(hits * 0.05, 0.30)

    return round(min(score, 1.0), 3)


def _page_has_transaction_signal(page_text: str) -> bool:
    text = (page_text or '').lower()
    header_hits = sum(1 for kw in HEADER_KEYWORDS if kw in text)
    has_date = bool(DATE_PATTERN.search(text) or DATE_WORD_PATTERN.search(text) or DATE_WORD_SHORT_PATTERN.search(text))
    has_amt = len(AMOUNT_PATTERN.findall(text)) >= 2
    return (header_hits >= 2 and has_date) or (has_date and has_amt) or (header_hits >= 3 and has_amt)


def _extract_amount_tokens(line: str) -> List[Tuple[float, Optional[str]]]:
    """
    Returns amount tokens from left-to-right as (value, direction)
    where direction is 'DR', 'CR', or None.
    """
    tokens: List[Tuple[float, Optional[str]]] = []
    amount_with_dir = re.finditer(
        r'(?P<num>\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2}))\s*(?P<dir>\(?\s*(?:DR|CR)\s*\)?)?',
        line,
        flags=re.IGNORECASE,
    )
    for m in amount_with_dir:
        num_str = (m.group('num') or '').replace(',', '')
        try:
            value = float(num_str)
        except Exception:
            continue
        raw_dir = (m.group('dir') or '').upper().replace('(', '').replace(')', '').strip()
        direction = raw_dir if raw_dir in ('DR', 'CR') else None
        tokens.append((value, direction))
    return tokens


def _row_from_aligned_statement_line(date_txt: str, line: str) -> Optional[dict]:
    """
    Parse text-extracted rows where columns survive only as whitespace.

    ICICI-like statements render as:
        1   02.11.2025        260.00          492.27
        2   02.11.2025                 10.22 502.49

    The amount with a large gap before the balance is in the withdrawal column;
    the amount adjacent to the balance is in the deposit column.
    """
    date_re = re.escape(date_txt or "")
    if not date_re:
        return None

    match = re.match(rf'^\s*\d{{1,6}}\s+{date_re}\s+', line, flags=re.IGNORECASE)
    if not match:
        return None

    tail = line[match.end():]
    amount_matches = list(AMOUNT_PATTERN.finditer(tail))
    if len(amount_matches) < 2:
        return None

    txn_match = amount_matches[-2]
    balance_match = amount_matches[-1]
    try:
        txn_amount = float(txn_match.group(0).replace(',', ''))
        balance = float(balance_match.group(0).replace(',', ''))
    except Exception:
        return None

    gap = balance_match.start() - txn_match.end()
    debit = txn_amount if gap >= 5 else None
    credit = txn_amount if gap < 5 else None

    return {
        'Date': date_txt,
        'Description': tail[:txn_match.start()].strip(),
        'Debit': debit,
        'Credit': credit,
        'Balance': balance,
        'Reference': None,
    }


def _row_from_line_and_meta(date_txt: str, line: str) -> Optional[dict]:
    aligned = _row_from_aligned_statement_line(date_txt, line)
    if aligned:
        return aligned

    # Keep date token, remove first date occurrence from description body.
    desc = line
    if date_txt:
        desc = re.sub(re.escape(date_txt), '', desc, count=1, flags=re.IGNORECASE).strip()
        if not line.lstrip().lower().startswith(date_txt.lower()):
            # Text statements often prefix rows with a serial number before the date.
            desc = re.sub(r'^\s*\d{1,6}\s+', '', desc).strip()

    # First: explicit +Rs/-Rs style (Paytm-like)
    pm = PLUS_MINUS_RS_PATTERN.search(line)
    if pm:
        sign, num = pm.group(1), pm.group(2)
        try:
            val = float(num.replace(',', ''))
        except Exception:
            val = None
        if val is not None:
            debit = val if sign == '-' else None
            credit = val if sign == '+' else None
            return {
                'Date': date_txt,
                'Description': re.sub(PLUS_MINUS_RS_PATTERN, '', desc).strip(),
                'Debit': debit,
                'Credit': credit,
                'Balance': None,
                'Reference': None,
            }

    amount_tokens = _extract_amount_tokens(line)
    if not amount_tokens:
        return None

    debit = None
    credit = None
    balance = None

    # Prefer explicit DR/CR markers first.
    directional = [t for t in amount_tokens if t[1] in ('DR', 'CR')]
    if directional:
        # Common public-sector format: transaction amount + balance with CR/DR suffix.
        if amount_tokens[-1][1] in ('DR', 'CR') and len(amount_tokens) >= 2 and amount_tokens[-2][1] is None:
            txn_value = amount_tokens[-2][0]
            balance = amount_tokens[-1][0]
            if amount_tokens[-1][1] == 'DR':
                balance = -abs(balance)
            desc_u = f" {desc.upper()} "
            if ' BY ' in desc_u and ' TO ' not in desc_u:
                credit = txn_value
            elif ' TO ' in desc_u or ' WITHDRAW' in desc_u or ' WDL ' in desc_u:
                debit = txn_value
            else:
                debit = txn_value
        else:
            for value, direction in directional[:-1]:
                if direction == 'DR' and debit is None:
                    debit = value
                elif direction == 'CR' and credit is None:
                    credit = value
            # Last token usually running balance for text statements.
            balance = amount_tokens[-1][0]
            if directional and directional[-1] == amount_tokens[-1] and len(amount_tokens) >= 2:
                balance = amount_tokens[-2][0]
    else:
        # Heuristic by trailing numeric columns: [debit, credit, balance] / [debit|credit, balance]
        n = len(amount_tokens)
        if n >= 3:
            debit = amount_tokens[-3][0]
            credit = amount_tokens[-2][0]
            balance = amount_tokens[-1][0]
        elif n == 2:
            first = amount_tokens[-2][0]
            second = amount_tokens[-1][0]
            # If second is larger/equal, treat as balance and first as transactional amount.
            balance = second
            desc_u = f" {desc.upper()} "
            if ' BY ' in desc_u and ' TO ' not in desc_u:
                credit = first
            elif ' TO ' in desc_u or ' WITHDRAW' in desc_u or ' WDL ' in desc_u:
                debit = first
            else:
                debit = first
        else:
            only = amount_tokens[-1][0]
            desc_u = f" {desc.upper()} "
            if ' BY ' in desc_u and ' TO ' not in desc_u:
                credit = only
            elif ' TO ' in desc_u or ' WITHDRAW' in desc_u or ' WDL ' in desc_u:
                debit = only
            else:
                balance = only

    # Remove trailing amount noise from description.
    desc = re.sub(r'\s*\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})\s*(?:\(?\s*(?:DR|CR)\s*\)?)?\s*$', '', desc, flags=re.IGNORECASE).strip()

    return {
        'Date': date_txt,
        'Description': desc,
        'Debit': debit,
        'Credit': credit,
        'Balance': balance,
        'Reference': None,
    }


def _build_rows_from_text(text: str) -> List[dict]:
    rows: List[dict] = []
    current: Optional[dict] = None

    for raw in (text or '').splitlines():
        raw_line = raw.rstrip()
        line = re.sub(r'\s+', ' ', raw).strip()
        if not line:
            continue

        # Ignore obvious page/summary/footer lines.
        if re.search(r'\b(page\s*\d+|page summary|brought forward|carried forward|opening balance|closing balance)\b', line, re.IGNORECASE):
            continue

        start = TXN_START_PATTERN.search(line)
        if start:
            if current:
                rows.append(current)
            date_txt = start.group(1)
            full_date = FULL_DATE_SEARCH_PATTERN.search(line)
            if date_txt.isdigit() and full_date:
                date_txt = full_date.group(0)
            current = _row_from_line_and_meta(date_txt, raw_line.strip() or line)
            if current is None:
                current = {'Date': date_txt, 'Description': line, 'Debit': None, 'Credit': None, 'Balance': None, 'Reference': None}
            continue

        # Continuation description lines append to previous txn.
        if current:
            extra = line
            pm = PLUS_MINUS_RS_PATTERN.search(extra)
            if pm:
                sign, num = pm.group(1), pm.group(2)
                try:
                    val = float(num.replace(',', ''))
                    if sign == '+':
                        current['Credit'] = val
                    else:
                        current['Debit'] = val
                except Exception:
                    pass
                extra = re.sub(PLUS_MINUS_RS_PATTERN, '', extra).strip()

            if DR_CR_PATTERN.search(extra):
                # Sometimes amount appears in continuation line.
                maybe = _row_from_line_and_meta(current.get('Date', ''), f"{current.get('Description', '')} {extra}")
                if maybe:
                    current.update({k: v for k, v in maybe.items() if k != 'Date'})
                    continue

            # Generic continuation with numeric amount/balance but no explicit DR/CR token.
            if current.get('Debit') is None and current.get('Credit') is None and AMOUNT_PATTERN.search(extra):
                maybe = _row_from_line_and_meta(current.get('Date', ''), f"{current.get('Description', '')} {extra}")
                if maybe:
                    current.update({k: v for k, v in maybe.items() if k != 'Date'})
                    continue
            current['Description'] = f"{current.get('Description', '')} {extra}".strip()

    if current:
        rows.append(current)

    # Keep only rows with at least date + (amount or balance).
    clean = []
    for r in rows:
        has_amt = any(r.get(k) is not None for k in ('Debit', 'Credit', 'Balance'))
        if r.get('Date') and has_amt:
            clean.append(r)
    return clean


def _repair_dc_from_description(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or 'Description' not in df.columns:
        return df
    df = df.copy()

    amt_re = re.compile(r'\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})')

    for i, row in df.iterrows():
        debit = row.get('Debit')
        credit = row.get('Credit')
        if debit is not None or credit is not None:
            continue

        desc = str(row.get('Description', '') or '')
        m = amt_re.search(desc)
        if not m:
            continue
        try:
            val = float(m.group(0).replace(',', ''))
        except Exception:
            continue

        desc_u = f" {desc.upper()} "
        if ' TO ' in desc_u or ' WITHDRAW' in desc_u or ' WDL ' in desc_u:
            df.at[i, 'Debit'] = val
        elif ' BY ' in desc_u:
            df.at[i, 'Credit'] = val

    return df


# ---------------------------------------------------------------------------
# Engine 1: pdfplumber (primary — best for grid tables)
# ---------------------------------------------------------------------------

def try_pdfplumber(pdf_path: str, password: Optional[str] = None) -> ExtractionResult:
    """
    Try multiple pdfplumber strategies per page, keep highest-scoring result.
    """
    strategies = [ 
        {"vertical_strategy": "lines", "horizontal_strategy": "lines",
         "snap_tolerance": 5, "join_tolerance": 3},
        {"vertical_strategy": "lines_strict", "horizontal_strategy": "lines_strict"},
        {"vertical_strategy": "lines", "horizontal_strategy": "lines",
         "snap_tolerance": 10, "join_tolerance": 5, "edge_min_length": 5},
        {"vertical_strategy": "text", "horizontal_strategy": "text", "intersection_tolerance": 10},
    ]

    best_dfs = []
    best_score = 0.0

    try:
        with pdfplumber.open(pdf_path, password=password) as pdf:
            total_pages = len(pdf.pages)

            for strategy in strategies:
                dfs = []
                for page in pdf.pages:
                    try:
                        candidates = page.extract_tables(table_settings=strategy) or []
                        for table in candidates:
                            if table and len(table) > 1:
                                df = pd.DataFrame(table)
                                s = score_table(df)
                                if s > 0.18:
                                    dfs.append(df)
                    except Exception:
                        continue

                if dfs:
                    avg = sum(score_table(d) for d in dfs) / len(dfs)
                    if avg > best_score:
                        best_score = avg
                        best_dfs = dfs

        if not best_dfs:
            return ExtractionResult([], 'pdfplumber', 0.0, 0.0)

        coverage = len(best_dfs) / max(total_pages, 1)
        return ExtractionResult(best_dfs, 'pdfplumber', best_score, coverage)

    except Exception as e:
        return ExtractionResult([], 'pdfplumber', 0.0, 0.0)


# ---------------------------------------------------------------------------
# Engine 2: PyMuPDF — Y-coordinate row clustering
# ---------------------------------------------------------------------------

def try_pymupdf(pdf_path: str, password: Optional[str] = None) -> ExtractionResult:
    """
    Reconstruct table rows from raw text blocks using Y-coordinate bucketing.
    """
    try:
        doc = fitz.open(pdf_path)
        if doc.is_encrypted:
            if not password or doc.authenticate(password) == 0:
                return ExtractionResult([], 'pymupdf', 0.0, 0.0)
        all_dfs = []

        for page in doc:
            blocks = page.get_text("dict")["blocks"]
            rows: dict = {}

            for block in blocks:
                if block.get("type") != 0:
                    continue
                for line in block["lines"]:
                    # Bucket Y by 6pt to merge close lines
                    y = round(line["bbox"][1] / 6) * 6
                    x = line["bbox"][0]
                    text = " ".join(s["text"] for s in line["spans"]).strip()
                    if text:
                        rows.setdefault(y, []).append((x, text))

            table_data = []
            for y in sorted(rows):
                row = [text for _, text in sorted(rows[y], key=lambda i: i[0])]
                table_data.append(row)

            if len(table_data) > 3:
                max_cols = max(len(r) for r in table_data)
                padded = [r + [''] * (max_cols - len(r)) for r in table_data]
                df = pd.DataFrame(padded)
                if score_table(df) > 0.18:
                    all_dfs.append(df)

        if not all_dfs:
            return ExtractionResult([], 'pymupdf', 0.0, 0.0)

        avg = sum(score_table(d) for d in all_dfs) / len(all_dfs)
        return ExtractionResult(all_dfs, 'pymupdf', avg, 1.0)

    except Exception as e:
        return ExtractionResult([], 'pymupdf', 0.0, 0.0)


def try_text_rows(pdf_path: str, password: Optional[str] = None) -> ExtractionResult:
    """
    Fallback parser for non-grid / legacy statements (IOB, UCO-like, Central Bank-like).
    Reads all pages, reconstructs transactions from text lines.
    """
    try:
        tables: List[pd.DataFrame] = []
        total_pages = 0
        hit_pages = 0

        with pdfplumber.open(pdf_path, password=password) as pdf:
            total_pages = len(pdf.pages)
            for page in pdf.pages:
                txt = page.extract_text(layout=True) or page.extract_text() or ""
                if not _page_has_transaction_signal(txt):
                    continue
                rows = _build_rows_from_text(txt)
                if rows:
                    hit_pages += 1
                    table_df = pd.DataFrame(rows)
                    table_df = _repair_dc_from_description(table_df)
                    tables.append(table_df)

        if not tables:
            return ExtractionResult([], 'text_rows', 0.0, 0.0)

        avg = sum(score_table(t) for t in tables) / max(len(tables), 1)
        # Strongly reward multi-page coverage for this fallback.
        coverage = hit_pages / max(total_pages, 1)
        merged = pd.concat([t.dropna(axis=1, how='all') for t in tables], ignore_index=True)
        debit_series = pd.to_numeric(merged.get('Debit', pd.Series(dtype=float)), errors='coerce').fillna(0)
        credit_series = pd.to_numeric(merged.get('Credit', pd.Series(dtype=float)), errors='coerce').fillna(0)
        non_zero_dc = int((debit_series > 0).sum()) + int((credit_series > 0).sum())
        if non_zero_dc == 0:
            quality_penalty = 0.55
        else:
            quality_penalty = 0.0

        debit_non_zero = int((debit_series > 0).sum())
        credit_non_zero = int((credit_series > 0).sum())
        if debit_non_zero == 0 or credit_non_zero == 0:
            quality_penalty += 0.12

        confidence = round(min(0.60, max(0.05, avg * 0.65 + coverage * 0.25 - quality_penalty)), 3)
        return ExtractionResult(tables, 'text_rows', confidence, coverage)
    except Exception:
        return ExtractionResult([], 'text_rows', 0.0, 0.0)


# ---------------------------------------------------------------------------
# Engine 3: Camelot (optional, if installed)
# ---------------------------------------------------------------------------

def try_camelot(pdf_path: str, flavor: str, password: Optional[str] = None) -> ExtractionResult:
    try:
        import camelot
        kwargs = {"pages": "all", "flavor": flavor}
        if password:
            kwargs["password"] = password
        if flavor == "lattice":
            kwargs["line_scale"] = 40
        else:
            kwargs.update({"edge_tol": 50, "row_tol": 10})

        tables = camelot.read_pdf(pdf_path, **kwargs)
        dfs = [t.df for t in tables if score_table(t.df) > 0.3]
        if not dfs:
            return ExtractionResult([], f'camelot_{flavor}', 0.0, 0.0)
        avg = sum(score_table(d) for d in dfs) / len(dfs)
        coverage = len(dfs) / max(len(tables), 1)
        return ExtractionResult(dfs, f'camelot_{flavor}', avg, coverage)
    except Exception:
        return ExtractionResult([], f'camelot_{flavor}', 0.0, 0.0)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def extract_best(pdf_path: str, password: Optional[str] = None) -> ExtractionResult:
    """
    Run all available engines, return the highest-confidence result.
    Prefers pdfplumber → camelot_lattice → camelot_stream → pymupdf.
    """
    results = [
        try_pdfplumber(pdf_path, password=password),
        try_camelot(pdf_path, 'lattice', password=password),
        try_camelot(pdf_path, 'stream', password=password),
        try_pymupdf(pdf_path, password=password),
        try_text_rows(pdf_path, password=password),
    ]

    # Rank by weighted score to avoid single-page high-confidence false winners.
    results.sort(
        key=lambda r: (round(r.confidence * 0.75 + min(r.page_coverage, 1.0) * 0.25, 4), r.confidence, r.page_coverage),
        reverse=True,
    )
    best = results[0]

    print(f"[Extractor] Engine scores:")
    for r in results:
        marker = "✓" if r is best else " "
        print(f"  {marker} {r.engine:<22} conf={r.confidence:.3f}  pages={r.page_coverage:.2f}")

    if best.confidence == 0.0:
        raise ValueError(f"All extraction engines failed for: {pdf_path}")

    return best
