
import re
import pdfplumber
import fitz
import pandas as pd
from dataclasses import dataclass, field
from typing import List

DATE_PATTERN = re.compile(r'\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b')
DATE_WORD_PATTERN = re.compile(
    r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b',
    re.IGNORECASE
)
# Matches numbers including Indian comma-formatted ones, optionally preceded by -/₹
AMOUNT_PATTERN = re.compile(r'\b\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?\b')

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

    if df is None or df.empty:
        return 0.0
    if len(df.columns) < 3 or len(df) < 2:
        return 0.0

    score = 0.0
    full_text = df.to_string().lower()

    # --- Date detection (numeric or word month) ---
    if DATE_PATTERN.search(full_text) or DATE_WORD_PATTERN.search(full_text):
        score += 0.35

    # --- Numeric amount detection ---
    # Count cells that are pure amounts (or '-' which means zero)
    numeric_cells = 0
    for col in df.columns:
        col_vals = df[col].astype(str).str.strip()
        # A column is "numeric" if >50% of values are amounts or dashes
        valid = col_vals.apply(
            lambda v: bool(AMOUNT_PATTERN.match(v.replace(',', ''))) or v == '-'
        )
        if valid.mean() > 0.5:
            numeric_cells += 1

    if numeric_cells >= 2:
        score += 0.35
    elif numeric_cells == 1:
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


# ---------------------------------------------------------------------------
# Engine 1: pdfplumber (primary — best for grid tables)
# ---------------------------------------------------------------------------

def try_pdfplumber(pdf_path: str) -> ExtractionResult:
    """
    Try multiple pdfplumber strategies per page, keep highest-scoring result.
    """
    strategies = [
        {"vertical_strategy": "lines", "horizontal_strategy": "lines",
         "snap_tolerance": 5, "join_tolerance": 3},
        {"vertical_strategy": "lines_strict", "horizontal_strategy": "lines_strict"},
        {"vertical_strategy": "lines", "horizontal_strategy": "lines",
         "snap_tolerance": 10, "join_tolerance": 5, "edge_min_length": 5},
    ]

    best_dfs = []
    best_score = 0.0

    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)

            for strategy in strategies:
                dfs = []
                for page in pdf.pages:
                    try:
                        table = page.extract_table(strategy)
                        if table and len(table) > 1:
                            df = pd.DataFrame(table)
                            s = score_table(df)
                            if s > 0.25:
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

def try_pymupdf(pdf_path: str) -> ExtractionResult:
    """
    Reconstruct table rows from raw text blocks using Y-coordinate bucketing.
    """
    try:
        doc = fitz.open(pdf_path)
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
                if score_table(df) > 0.25:
                    all_dfs.append(df)

        if not all_dfs:
            return ExtractionResult([], 'pymupdf', 0.0, 0.0)

        avg = sum(score_table(d) for d in all_dfs) / len(all_dfs)
        return ExtractionResult(all_dfs, 'pymupdf', avg, 1.0)

    except Exception as e:
        return ExtractionResult([], 'pymupdf', 0.0, 0.0)


# ---------------------------------------------------------------------------
# Engine 3: Camelot (optional, if installed)
# ---------------------------------------------------------------------------

def try_camelot(pdf_path: str, flavor: str) -> ExtractionResult:
    try:
        import camelot
        kwargs = {"pages": "all", "flavor": flavor}
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

def extract_best(pdf_path: str) -> ExtractionResult:
    """
    Run all available engines, return the highest-confidence result.
    Prefers pdfplumber -> camelot_lattice -> camelot_stream -> pymupdf.
    """
    results = [
        try_pdfplumber(pdf_path),
        try_camelot(pdf_path, 'lattice'),
        try_camelot(pdf_path, 'stream'),
        try_pymupdf(pdf_path),
    ]

    # Sort by confidence first, then page_coverage as tiebreaker
    results.sort(key=lambda r: (r.confidence, r.page_coverage), reverse=True)
    best = results[0]

    print(f"[Extractor] Engine scores:")
    for r in results:
        marker = "✓" if r is best else " "
        print(f"  {marker} {r.engine:<22} conf={r.confidence:.3f}  pages={r.page_coverage:.2f}")

    if best.confidence == 0.0:
        raise ValueError(f"All extraction engines failed for: {pdf_path}")

    return best
