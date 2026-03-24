"""
Post-extraction validation with balance continuity arithmetic check.
"""

import pandas as pd
from dataclasses import dataclass, field
from typing import List

BALANCE_TOLERANCE = 2.0   # ₹2 rounding tolerance


@dataclass
class ValidationReport:
    total_rows: int = 0
    valid_rows: int = 0
    balance_mismatches: List[int] = field(default_factory=list)
    missing_dates: int = 0
    missing_descriptions: int = 0
    suspicious_rows: List[int] = field(default_factory=list)
    passed: bool = False
    confidence_score: float = 0.0
    notes: List[str] = field(default_factory=list)


def validate(df: pd.DataFrame) -> ValidationReport:
    report = ValidationReport()
    report.total_rows = len(df)

    if df.empty:
        report.notes.append("DataFrame is empty.")
        return report

    # 1. Date completeness
    report.missing_dates = int(df['Date'].isna().sum())

    # 2. Description completeness
    report.missing_descriptions = int(
        (df['Description'].isna() | (df['Description'].astype(str).str.strip() == '')).sum()
    )

    # 3. Balance continuity check
    has_balance = df['Balance'].notna().sum() > 3
    if has_balance:
        for i in range(1, len(df)):
            prev_bal = df.iloc[i - 1]['Balance']
            curr_bal = df.iloc[i]['Balance']
            debit  = df.iloc[i]['Debit']  or 0.0
            credit = df.iloc[i]['Credit'] or 0.0

            if pd.notna(prev_bal) and pd.notna(curr_bal):
                expected = round(float(prev_bal) - float(debit) + float(credit), 2)
                actual   = round(float(curr_bal), 2)
                if abs(expected - actual) > BALANCE_TOLERANCE:
                    report.balance_mismatches.append(i)
    else:
        report.notes.append("Balance column missing or sparse — arithmetic check skipped.")

    # 4. Both debit AND credit filled on the same row (usually wrong)
    both = df[(df['Debit'].notna() & df['Debit'].apply(lambda x: x is not None and x > 0)) &
              (df['Credit'].notna() & df['Credit'].apply(lambda x: x is not None and x > 0))]
    report.suspicious_rows = both.index.tolist()
    if report.suspicious_rows:
        report.notes.append(
            f"{len(report.suspicious_rows)} rows have both Debit and Credit filled — review."
        )

    # 5. Confidence score
    date_score    = 1 - (report.missing_dates / report.total_rows)
    balance_score = 1 - (len(report.balance_mismatches) / max(report.total_rows, 1))
    desc_score    = 1 - (report.missing_descriptions / report.total_rows)

    report.confidence_score = round(
        date_score * 0.35 + balance_score * 0.45 + desc_score * 0.20, 3
    )
    report.valid_rows = report.total_rows - len(report.balance_mismatches)
    report.passed = report.confidence_score >= 0.80

    return report
