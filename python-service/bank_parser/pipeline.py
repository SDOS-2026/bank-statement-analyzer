"""
pipeline.py — Universal bank statement parser
Supports: PDF, XLSX, XLS, ODS, CSV
"""

import os, sys
_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import pandas as pd
import fitz
from dataclasses import asdict

from extractor.engine_runner import extract_best
from extractor.excel_engine import is_spreadsheet, extract_spreadsheet, check_spreadsheet_encrypted
from processors.header_detector import split_header_and_data
from semantic.column_mapper import apply_column_mapping
from semantic.bank_detector import detect_bank, get_bank_overrides, normalize_bank_name
from semantic.categorizer import categorize_dataframe
from processors.reconstructor import reconstruct
from validators.transaction_validator import validate
from analytics.insights import compute_insights, compute_scorecard


def parse_bank_statement(file_path: str, password: str = None, bank_hint: str = None) -> dict:
    if is_spreadsheet(file_path):
        return _parse_spreadsheet(file_path, password)
    return _parse_pdf(file_path, password, bank_hint=bank_hint)


def _parse_pdf(pdf_path: str, password: str = None, bank_hint: str = None) -> dict:
    encryption_status = _pdf_encryption_status(pdf_path, password)
    if encryption_status:
        return {"dataframe": pd.DataFrame(), "bank": "UNKNOWN",
                "engine_used": "pdf", "validation": None,
                "success": False, "status": encryption_status,
                "insights": {}, "scorecard": {}}

    bank = normalize_bank_name(bank_hint) if bank_hint else "UNKNOWN"
    if bank == "UNKNOWN":
        bank = detect_bank(pdf_path, password=password)
    else:
        print(f"[Pipeline] Using bank hint: {bank_hint} -> {bank}", flush=True)
    overrides = get_bank_overrides(bank)
    print(f"[Pipeline] Detected bank: {bank}", flush=True)

    extraction = extract_best(pdf_path, password=password)
    combined = pd.concat([t.dropna(axis=1, how='all') for t in extraction.tables], ignore_index=True)
    print(f"[Pipeline] Raw combined shape: {combined.shape}", flush=True)

    canonical_cols = {'date', 'description', 'debit', 'credit', 'balance'}
    lower_cols = {str(c).strip().lower() for c in combined.columns}

    if canonical_cols.issubset(lower_cols):
        df = combined.copy()
        print(f"[Pipeline] Using pre-standardized rows from engine={extraction.engine}", flush=True)
    else:
        df, _ = split_header_and_data(combined)
        print(f"[Pipeline] After header strip: {len(df)} rows | cols: {list(df.columns)}", flush=True)

    df = apply_column_mapping(df, bank_overrides=overrides)
    df = reconstruct(df)
    print(f"[Pipeline] After reconstruction: {len(df)} rows", flush=True)
    return _finalize(df, bank, extraction.engine)


def _pdf_encryption_status(pdf_path: str, password: str = None) -> str | None:
    try:
        doc = fitz.open(pdf_path)
        if not doc.is_encrypted:
            doc.close()
            return None
        if not password:
            doc.close()
            return "password_required"
        ok = doc.authenticate(password) != 0
        doc.close()
        return None if ok else "wrong_password"
    except Exception:
        return None


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

    combined = pd.concat([t.dropna(axis=1, how='all') for t in result.tables], ignore_index=True)
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
