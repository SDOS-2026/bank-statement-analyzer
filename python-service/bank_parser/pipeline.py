"""
pipeline.py — Universal bank statement parser
Supports: PDF, XLSX, XLS, ODS, CSV
"""

import os, sys
_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import pandas as pd
from dataclasses import asdict

from extractor.engine_runner import extract_best
from extractor.excel_engine import is_spreadsheet, extract_spreadsheet, check_spreadsheet_encrypted
from processors.header_detector import split_header_and_data
from semantic.column_mapper import apply_column_mapping
from semantic.bank_detector import detect_bank, get_bank_overrides
from semantic.categorizer import categorize_dataframe
from processors.reconstructor import reconstruct
from validators.transaction_validator import validate
from analytics.insights import compute_insights, compute_scorecard


def parse_bank_statement(file_path: str, password: str = None) -> dict:
    if not file_path:
        raise ValueError("file_path cannot be empty")

    is_sheet = is_spreadsheet(file_path)

    parser = _parse_spreadsheet if is_sheet else _parse_pdf

    return parser(file_path, password)


def _parse_pdf(pdf_path: str, password: str = None) -> dict:
    bank = detect_bank(pdf_path)
    overrides = get_bank_overrides(bank)
    print(f"[Pipeline] Detected bank: {bank}", flush=True)

    extraction = extract_best(pdf_path)

    # Safer concat (handles empty tables case)
    tables = extraction.tables or []
    combined = pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()
    print(f"[Pipeline] Raw combined shape: {combined.shape}", flush=True)

    df, _ = split_header_and_data(combined)
    print(f"[Pipeline] After header strip: {len(df)} rows | cols: {list(df.columns)}", flush=True)

    # Apply transformations step-by-step (same logic, clearer flow)
    df = apply_column_mapping(df, bank_overrides=overrides)
    df = reconstruct(df)

    print(f"[Pipeline] After reconstruction: {len(df)} rows", flush=True)

    return _finalize(df, bank, extraction.engine)

def _parse_spreadsheet(file_path: str, password: str = None) -> dict:
    ext = os.path.splitext(file_path)[1].lower()

    if check_spreadsheet_encrypted(file_path) and not password:
        return {"dataframe": pd.DataFrame(), "bank": "UNKNOWN",
                "engine_used": f"excel{ext}", "validation": None,
                "success": False, "status": "password_required",
                "insights": {}, "scorecard": {}}

    result = extract_spreadsheet(file_path, password)

    if result.encrypted and not password:
        return {"dataframe": pd.DataFrame(), "bank": "UNKNOWN",
                "engine_used": result.engine, "validation": None,
                "success": False, "status": "password_required",
                "insights": {}, "scorecard": {}}

    if not result.tables:
        raise ValueError(f"No usable data found in: {file_path}")

    combined = pd.concat(result.tables, ignore_index=True)
    print(f"[Pipeline] Spreadsheet raw shape: {combined.shape}", flush=True)

    df = apply_column_mapping(combined)
    df = reconstruct(df)
    print(f"[Pipeline] After reconstruction: {len(df)} rows", flush=True)
    return _finalize(df, "UNKNOWN", result.engine)


def _finalize(df: pd.DataFrame, bank: str, engine: str) -> dict:
    report = validate(df)
    print(f"[Pipeline] Rows={report.total_rows} | Confidence={report.confidence_score:.1%} | "
          f"Mismatches={len(report.balance_mismatches)}", flush=True)

    if not df.empty:
        df = categorize_dataframe(df)
        print(f"[Pipeline] Categories: {df['Category'].value_counts().to_dict()}", flush=True)

    insights_obj  = compute_insights(df)
    scorecard_obj = compute_scorecard(insights_obj)
    print(f"[Pipeline] Score: {scorecard_obj.final_score}/100 ({scorecard_obj.risk_band})", flush=True)

    return {
        "dataframe":   df,
        "bank":        bank,
        "engine_used": engine,
        "validation":  report,
        "success":     report.passed,
        "insights":    asdict(insights_obj),
        "scorecard":   asdict(scorecard_obj),
        "status":      "success",
    }
