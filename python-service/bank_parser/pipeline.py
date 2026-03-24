"""
Main pipeline: PDF → clean transaction DataFrame
"""

import pandas as pd
from extractor.engine_runner import extract_best
from processors.header_detector import split_header_and_data
from semantic.column_mapper import apply_column_mapping
from semantic.bank_detector import detect_bank, get_bank_overrides
from processors.reconstructor import reconstruct
from validators.transaction_validator import validate


def parse_bank_statement(pdf_path: str) -> dict:
    """
    Returns:
        {
            "dataframe":    pd.DataFrame,
            "bank":         str,
            "engine_used":  str,
            "validation":   ValidationReport,
            "success":      bool,
        }
    """
    # 1. Detect bank from letterhead only
    bank = detect_bank(pdf_path)
    overrides = get_bank_overrides(bank)
    print(f"[Pipeline] Detected bank: {bank}")

    # 2. Extract raw tables (multi-engine waterfall)
    extraction = extract_best(pdf_path)

    # 3. Merge all pages (they're continuation of the same statement)
    combined = pd.concat(extraction.tables, ignore_index=True)
    print(f"[Pipeline] Raw combined shape: {combined.shape}")

    # 4. Isolate header and data rows
    df, raw_cols = split_header_and_data(combined)
    print(f"[Pipeline] After header strip: {len(df)} rows | cols: {list(df.columns)}")

    # 5. Map columns to standard schema
    df = apply_column_mapping(df, bank_overrides=overrides)
    print(f"[Pipeline] After column mapping: {list(df.columns)}")

    # 6. Structural reconstruction
    df = reconstruct(df)
    print(f"[Pipeline] After reconstruction: {len(df)} rows")

    # 7. Validate
    report = validate(df)

    print(f"[Pipeline] Rows={report.total_rows} | "
          f"Confidence={report.confidence_score:.1%} | "
          f"BalanceMismatches={len(report.balance_mismatches)}")
    if report.notes:
        for note in report.notes:
            print(f"[Pipeline] NOTE: {note}")

    if not report.passed:
        print(f"[Pipeline] ⚠ Low confidence — manual review recommended.")

    return {
        "dataframe":   df,
        "bank":        bank,
        "engine_used": extraction.engine,
        "validation":  report,
        "success":     report.passed,
    }
