"""
Advanced post-extraction validation with:
- Balance continuity
- Duplicate detection
- Date parsing consistency
- Negative value anomaly detection
- Outlier transaction flagging
- Missing field checks
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

BALANCE_TOLERANCE = 2.0   # ₹2 rounding tolerance
LARGE_TRANSACTION_FACTOR = 3.0  # z-score threshold


@dataclass
class ValidationReport:
    total_rows: int = 0
    valid_rows: int = 0

    # Core issues
    balance_mismatches: List[int] = field(default_factory=list)
    suspicious_rows: List[int] = field(default_factory=list)
    duplicate_rows: List[int] = field(default_factory=list)
    invalid_date_rows: List[int] = field(default_factory=list)
    negative_value_rows: List[int] = field(default_factory=list)
    outlier_rows: List[int] = field(default_factory=list)

    # Missing data
    missing_dates: int = 0
    missing_descriptions: int = 0
    missing_balance: int = 0

    # Overall
    passed: bool = False
    confidence_score: float = 0.0
    notes: List[str] = field(default_factory=list)


def _amount_or_zero(value) -> float:
    if pd.isna(value):
        return 0.0
    try:
        return float(value)
    except Exception:
        return 0.0


def _safe_to_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors='coerce', dayfirst=True)


def _balance_mismatches(df: pd.DataFrame, reverse_order: bool = False) -> List[int]:
    mismatches: List[int] = []

    for i in range(1, len(df)):
        prev_bal = df.iloc[i - 1]['Balance']
        curr_bal = df.iloc[i]['Balance']

        amount_row = df.iloc[i - 1] if reverse_order else df.iloc[i]

        debit = _amount_or_zero(amount_row['Debit'])
        credit = _amount_or_zero(amount_row['Credit'])

        if pd.notna(prev_bal) and pd.notna(curr_bal):
            if reverse_order:
                expected = round(float(prev_bal) + debit - credit, 2)
            else:
                expected = round(float(prev_bal) - debit + credit, 2)

            actual = round(float(curr_bal), 2)

            if abs(expected - actual) > BALANCE_TOLERANCE:
                mismatches.append(i)

    return mismatches


def _detect_duplicates(df: pd.DataFrame) -> List[int]:
    duplicate_mask = df.duplicated(
        subset=['Date', 'Description', 'Debit', 'Credit', 'Balance'],
        keep=False
    )
    return df[duplicate_mask].index.tolist()


def _invalid_dates(df: pd.DataFrame) -> List[int]:
    parsed = _safe_to_datetime(df['Date'])
    return df[parsed.isna()].index.tolist()


def _negative_value_rows(df: pd.DataFrame) -> List[int]:
    rows = []

    for idx, row in df.iterrows():
        for col in ['Debit', 'Credit', 'Balance']:
            try:
                if pd.notna(row[col]) and float(row[col]) < 0:
                    rows.append(idx)
                    break
            except Exception:
                continue

    return rows


def _outlier_rows(df: pd.DataFrame) -> List[int]:
    amounts = (
        pd.to_numeric(df['Debit'], errors='coerce').fillna(0) +
        pd.to_numeric(df['Credit'], errors='coerce').fillna(0)
    )

    if amounts.std() == 0:
        return []

    z_scores = np.abs((amounts - amounts.mean()) / amounts.std())

    return df[z_scores > LARGE_TRANSACTION_FACTOR].index.tolist()


def validate(df: pd.DataFrame) -> ValidationReport:
    report = ValidationReport()
    report.total_rows = len(df)

    if df.empty:
        report.notes.append("DataFrame is empty.")
        return report

    # Normalize expected columns
    required_cols = ['Date', 'Description', 'Debit', 'Credit', 'Balance']
    for col in required_cols:
        if col not in df.columns:
            df[col] = np.nan
            report.notes.append(f"Missing column '{col}' was auto-created.")

    # 1. Missing field checks
    report.missing_dates = int(df['Date'].isna().sum())

    report.missing_descriptions = int(
        (df['Description'].isna() |
         (df['Description'].astype(str).str.strip() == '')).sum()
    )

    report.missing_balance = int(df['Balance'].isna().sum())

    # 2. Invalid date parsing
    report.invalid_date_rows = _invalid_dates(df)
    if report.invalid_date_rows:
        report.notes.append(
            f"{len(report.invalid_date_rows)} rows contain invalid date formats."
        )

    # 3. Balance continuity
    has_balance = df['Balance'].notna().sum() > 3

    if has_balance:
        forward = _balance_mismatches(df, reverse_order=False)
        reverse = _balance_mismatches(df, reverse_order=True)

        if len(reverse) < len(forward):
            report.balance_mismatches = reverse
            report.notes.append(
                "Balance continuity matched reverse-chronological statement order."
            )
        else:
            report.balance_mismatches = forward
    else:
        report.notes.append(
            "Balance column missing or sparse — arithmetic check skipped."
        )

    # 4. Debit + Credit both positive
    debit_positive = pd.to_numeric(df['Debit'], errors='coerce').fillna(0) > 0
    credit_positive = pd.to_numeric(df['Credit'], errors='coerce').fillna(0) > 0

    both = df[debit_positive & credit_positive]

    report.suspicious_rows = both.index.tolist()

    if report.suspicious_rows:
        report.notes.append(
            f"{len(report.suspicious_rows)} rows have both Debit and Credit filled."
        )

    # 5. Duplicate transaction detection
    report.duplicate_rows = _detect_duplicates(df)

    if report.duplicate_rows:
        report.notes.append(
            f"{len(report.duplicate_rows)} potential duplicate transactions detected."
        )

    # 6. Negative values
    report.negative_value_rows = _negative_value_rows(df)

    if report.negative_value_rows:
        report.notes.append(
            f"{len(report.negative_value_rows)} rows contain negative financial values."
        )

    # 7. Outlier transaction detection
    report.outlier_rows = _outlier_rows(df)

    if report.outlier_rows:
        report.notes.append(
            f"{len(report.outlier_rows)} unusually large transactions detected."
        )

    # 8. Confidence score
    date_score = 1 - ((report.missing_dates + len(report.invalid_date_rows)) / report.total_rows)

    balance_score = 1 - (len(report.balance_mismatches) / report.total_rows)

    desc_score = 1 - (report.missing_descriptions / report.total_rows)

    duplicate_penalty = 1 - (len(report.duplicate_rows) / report.total_rows)

    anomaly_penalty = 1 - (
        (len(report.negative_value_rows) + len(report.suspicious_rows)) / report.total_rows
    )

    report.confidence_score = round(
        (
            date_score * 0.25 +
            balance_score * 0.35 +
            desc_score * 0.15 +
            duplicate_penalty * 0.15 +
            anomaly_penalty * 0.10
        ),
        3
    )

    report.valid_rows = (
        report.total_rows
        - len(report.balance_mismatches)
        - len(report.invalid_date_rows)
    )

    report.passed = report.confidence_score >= 0.80

    return report