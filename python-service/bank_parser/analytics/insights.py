"""
analytics/insights.py

Three analytical layers:
  1. EMIDetector      — finds recurring fixed debits (loan EMIs)
  2. FinancialInsights — monthly aggregates, savings rate, bounce detection
  3. UnderwrightingScorecard — loan eligibility score 0-100
"""

from __future__ import annotations
import re
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Optional
import pandas as pd
import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# 1. EMI DETECTOR
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DetectedEMI:
    amount: float
    frequency: str          # "monthly" | "bi-monthly" | "weekly"
    occurrences: int
    description_sample: str
    months_detected: list[str]
    confidence: float       # 0–1


def detect_emis(df: pd.DataFrame) -> list[dict]:
    """
    Detect recurring fixed-amount debits that look like EMIs.

    Algorithm:
      - Group debit transactions by rounded amount (±2% tolerance)
      - Check if they recur on a monthly cadence (±7 day tolerance)
      - Require at least 2 occurrences
      - Boost confidence if description contains EMI/NACH/loan keywords
    """
    EMI_KEYWORDS = re.compile(
        r'emi|nach|loan|ecs|standing|auto.?debit|mortgage|finance|credit.?card',
        re.IGNORECASE
    )

    if df.empty or 'Debit' not in df.columns or 'Date' not in df.columns:
        return []

    debits = df[df['Debit'].notna() & (df['Debit'] > 0)].copy()
    if debits.empty:
        return []

    debits = debits.sort_values('Date').reset_index(drop=True)
    debits['_month'] = debits['Date'].dt.to_period('M').astype(str)

    # Group by amount bucket (round to nearest 50 to handle minor variations)
    def _bucket(amount: float) -> int:
        return int(round(amount / 50.0) * 50)

    debits['_bucket'] = debits['Debit'].apply(_bucket)

    emis: list[DetectedEMI] = []
    seen_buckets = set()

    for bucket, group in debits.groupby('_bucket'):
        if bucket in seen_buckets or len(group) < 2:
            continue

        # Check amount consistency (within 2%)
        amounts = group['Debit'].values
        mean_amt = float(np.mean(amounts))
        cv = float(np.std(amounts) / mean_amt) if mean_amt > 0 else 1.0
        if cv > 0.05:   # more than 5% coefficient of variation → not EMI
            continue

        # Check temporal cadence
        dates = sorted(group['Date'].dropna().tolist())
        if len(dates) < 2:
            continue

        gaps_days = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
        avg_gap = float(np.mean(gaps_days))

        if 25 <= avg_gap <= 35:
            frequency = "monthly"
        elif 55 <= avg_gap <= 65:
            frequency = "bi-monthly"
        elif 6 <= avg_gap <= 8:
            frequency = "weekly"
        else:
            continue  # not a recognizable cadence

        # Confidence scoring
        confidence = 0.5
        if len(group) >= 3:
            confidence += 0.2
        if len(group) >= 6:
            confidence += 0.1
        # Gap consistency
        gap_std = float(np.std(gaps_days)) if len(gaps_days) > 1 else 0
        if gap_std < 5:
            confidence += 0.15

        # Keyword boost
        desc_text = ' '.join(str(d) for d in group['Description'].fillna('').values).lower()
        if EMI_KEYWORDS.search(desc_text):
            confidence += 0.15

        confidence = round(min(confidence, 1.0), 2)

        months = sorted(group['_month'].unique().tolist())
        desc_sample = str(group.iloc[0].get('Description', ''))[:80]

        emis.append(DetectedEMI(
            amount=round(mean_amt, 2),
            frequency=frequency,
            occurrences=int(len(group)),
            description_sample=desc_sample,
            months_detected=months,
            confidence=confidence,
        ))
        seen_buckets.add(bucket)

    # Sort by confidence desc, then amount desc
    emis.sort(key=lambda e: (-e.confidence, -e.amount))

    return [asdict(e) for e in emis]


# ─────────────────────────────────────────────────────────────────────────────
# 2. FINANCIAL INSIGHTS ENGINE
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MonthlyBreakdown:
    month: str
    income: float
    expenses: float
    emi_outflow: float
    savings: float
    savings_rate: float     # %
    avg_balance: float
    transaction_count: int


@dataclass
class FinancialInsights:
    # Period
    period_start: str
    period_end: str
    months_analyzed: int

    # Totals
    total_income: float
    total_expenses: float
    total_emi: float
    net_savings: float

    # Averages
    avg_monthly_income: float
    avg_monthly_expenses: float
    avg_monthly_savings: float
    avg_balance: float
    savings_rate: float             # overall %

    # EMI
    emi_burden_ratio: float         # EMI / Income %
    detected_emis: list[dict]
    emi_count: int

    # Income stability
    income_stability_score: float   # 0–1 (low CV = stable)
    income_months: int              # how many months had income

    # Risk signals
    bounce_count: int               # months where balance < 1000 at any point
    low_balance_months: list[str]
    negative_balance_months: list[str]

    # Category breakdown
    category_totals: dict[str, float]   # {category: total_spend}
    top_expense_categories: list[dict]  # [{category, amount, pct}]

    # Monthly detail
    monthly_breakdown: list[dict]


def compute_insights(df: pd.DataFrame) -> FinancialInsights:
    """Compute full financial picture from a categorized transactions DataFrame."""

    INCOME_CATS = {
        'SALARY', 'BUSINESS_INCOME', 'FREELANCE',
        'INTEREST', 'DIVIDEND', 'REFUND', 'CASHBACK', 'CASH_DEPOSIT'
    }
    EMI_CATS = {'EMI'}

    if df.empty:
        return _empty_insights()

    df = df.copy()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    df['_month'] = df['Date'].dt.to_period('M').astype(str)
    df['_debit']  = pd.to_numeric(df.get('Debit',  pd.Series(dtype=float)), errors='coerce').fillna(0)
    df['_credit'] = pd.to_numeric(df.get('Credit', pd.Series(dtype=float)), errors='coerce').fillna(0)
    df['_balance'] = pd.to_numeric(df.get('Balance', pd.Series(dtype=float)), errors='coerce')
    cat_col = 'Category' if 'Category' in df.columns else None

    period_start = str(df['Date'].min().date()) if not df.empty else ''
    period_end   = str(df['Date'].max().date()) if not df.empty else ''
    months       = sorted(df['_month'].unique().tolist())
    n_months     = max(len(months), 1)

    # ── Totals ────────────────────────────────────────────────────────────────
    total_income   = 0.0
    total_expenses = 0.0
    total_emi      = 0.0

    if cat_col:
        income_mask   = df[cat_col].isin(INCOME_CATS)
        emi_mask      = df[cat_col].isin(EMI_CATS)
        expense_mask  = ~income_mask

        total_income   = float(df.loc[income_mask,  '_credit'].sum())
        total_emi      = float(df.loc[emi_mask,     '_debit'].sum())
        total_expenses = float(df['_debit'].sum())   # all debits = expenses
    else:
        total_income   = float(df['_credit'].sum())
        total_expenses = float(df['_debit'].sum())
        total_emi      = 0.0

    net_savings = total_income - total_expenses

    # ── Averages ──────────────────────────────────────────────────────────────
    avg_monthly_income   = total_income   / n_months
    avg_monthly_expenses = total_expenses / n_months
    avg_monthly_savings  = net_savings    / n_months
    savings_rate = round((net_savings / total_income * 100), 2) if total_income > 0 else 0.0
    avg_balance  = float(df['_balance'].dropna().mean()) if df['_balance'].notna().sum() > 0 else 0.0

    # ── Income stability ──────────────────────────────────────────────────────
    monthly_income: dict[str, float] = {}
    for m in months:
        mdf = df[df['_month'] == m]
        if cat_col:
            mi = float(mdf.loc[mdf[cat_col].isin(INCOME_CATS), '_credit'].sum())
        else:
            mi = float(mdf['_credit'].sum())
        monthly_income[m] = mi

    income_vals = [v for v in monthly_income.values() if v > 0]
    income_months = len(income_vals)

    if len(income_vals) >= 2:
        cv = float(np.std(income_vals) / np.mean(income_vals)) if np.mean(income_vals) > 0 else 1.0
        income_stability = round(max(0.0, 1.0 - cv), 3)
    elif len(income_vals) == 1:
        income_stability = 0.5
    else:
        income_stability = 0.0

    # ── EMI burden ───────────────────────────────────────────────────────────
    emi_burden = round((total_emi / total_income * 100), 2) if total_income > 0 else 0.0

    # ── Bounce / low balance detection ───────────────────────────────────────
    LOW_BAL_THRESHOLD = 1000.0
    bounce_months: list[str] = []
    negative_months: list[str] = []

    for m in months:
        mdf = df[df['_month'] == m]
        bal_vals = mdf['_balance'].dropna()
        if bal_vals.empty:
            continue
        min_bal = float(bal_vals.min())
        if min_bal < 0:
            negative_months.append(m)
        elif min_bal < LOW_BAL_THRESHOLD:
            bounce_months.append(m)

    # ── Category breakdown ────────────────────────────────────────────────────
    category_totals: dict[str, float] = {}
    if cat_col:
        for cat, grp in df[df['_debit'] > 0].groupby(cat_col):
            category_totals[str(cat)] = round(float(grp['_debit'].sum()), 2)

    # Top 5 expense categories
    sorted_cats = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    top_expense = [
        {
            'category': c,
            'amount': round(a, 2),
            'pct': round(a / total_expenses * 100, 1) if total_expenses > 0 else 0.0
        }
        for c, a in sorted_cats[:5]
    ]

    # ── Monthly breakdown ─────────────────────────────────────────────────────
    monthly_breakdown: list[dict] = []
    for m in months:
        mdf = df[df['_month'] == m]
        if cat_col:
            m_income   = float(mdf.loc[mdf[cat_col].isin(INCOME_CATS), '_credit'].sum())
            m_emi      = float(mdf.loc[mdf[cat_col].isin(EMI_CATS),    '_debit'].sum())
        else:
            m_income = float(mdf['_credit'].sum())
            m_emi    = 0.0

        m_expenses = float(mdf['_debit'].sum())
        m_savings  = m_income - m_expenses
        m_savings_rate = round((m_savings / m_income * 100), 1) if m_income > 0 else 0.0
        m_avg_bal  = float(mdf['_balance'].dropna().mean()) if mdf['_balance'].notna().sum() > 0 else 0.0

        monthly_breakdown.append(asdict(MonthlyBreakdown(
            month=m,
            income=round(m_income, 2),
            expenses=round(m_expenses, 2),
            emi_outflow=round(m_emi, 2),
            savings=round(m_savings, 2),
            savings_rate=m_savings_rate,
            avg_balance=round(m_avg_bal, 2),
            transaction_count=int(len(mdf)),
        )))

    # ── EMI detection ─────────────────────────────────────────────────────────
    detected_emis = detect_emis(df)

    return FinancialInsights(
        period_start=period_start,
        period_end=period_end,
        months_analyzed=n_months,
        total_income=round(total_income, 2),
        total_expenses=round(total_expenses, 2),
        total_emi=round(total_emi, 2),
        net_savings=round(net_savings, 2),
        avg_monthly_income=round(avg_monthly_income, 2),
        avg_monthly_expenses=round(avg_monthly_expenses, 2),
        avg_monthly_savings=round(avg_monthly_savings, 2),
        avg_balance=round(avg_balance, 2),
        savings_rate=savings_rate,
        emi_burden_ratio=emi_burden,
        detected_emis=detected_emis,
        emi_count=len(detected_emis),
        income_stability_score=income_stability,
        income_months=income_months,
        bounce_count=len(bounce_months),
        low_balance_months=bounce_months,
        negative_balance_months=negative_months,
        category_totals=category_totals,
        top_expense_categories=top_expense,
        monthly_breakdown=monthly_breakdown,
    )


def _empty_insights() -> FinancialInsights:
    return FinancialInsights(
        period_start='', period_end='', months_analyzed=0,
        total_income=0, total_expenses=0, total_emi=0, net_savings=0,
        avg_monthly_income=0, avg_monthly_expenses=0, avg_monthly_savings=0,
        avg_balance=0, savings_rate=0, emi_burden_ratio=0,
        detected_emis=[], emi_count=0,
        income_stability_score=0, income_months=0,
        bounce_count=0, low_balance_months=[], negative_balance_months=[],
        category_totals={}, top_expense_categories=[], monthly_breakdown=[],
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. UNDERWRITING SCORECARD
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ScorecardComponent:
    name: str
    score: int          # raw points earned
    max_score: int      # max possible points
    weight: float       # contribution to final score
    reasoning: str


@dataclass
class UnderwrightingScorecard:
    final_score: int            # 0–100
    risk_band: str              # EXCELLENT / GOOD / FAIR / POOR / VERY_POOR
    loan_recommendation: str
    components: list[dict]
    summary: str


def compute_scorecard(insights: FinancialInsights) -> UnderwrightingScorecard:
    """
    Rule-based underwriting scorecard.

    Components (total 100 pts):
      1. Income Stability     (25 pts)
      2. EMI Burden Ratio     (20 pts)
      3. Savings Behaviour    (20 pts)
      4. Balance Consistency  (15 pts)
      5. Bounce/Risk Signals  (10 pts)
      6. Income Level         (10 pts)
    """
    components: list[ScorecardComponent] = []

    # ── 1. Income Stability (25 pts) ─────────────────────────────────────────
    stab = insights.income_stability_score
    if stab >= 0.90:
        s1, r1 = 25, "Highly stable income across all months"
    elif stab >= 0.75:
        s1, r1 = 20, "Mostly stable income with minor variation"
    elif stab >= 0.55:
        s1, r1 = 14, "Moderate income variability detected"
    elif stab >= 0.30:
        s1, r1 = 8,  "High income variability — irregular earning pattern"
    else:
        s1, r1 = 3,  "Very unstable or absent income detected"

    if insights.income_months < 3:
        s1 = max(0, s1 - 8)
        r1 += f"; only {insights.income_months} month(s) of income detected"

    components.append(ScorecardComponent("Income Stability", s1, 25, 0.25, r1))

    # ── 2. EMI Burden Ratio (20 pts) ─────────────────────────────────────────
    ebr = insights.emi_burden_ratio
    if ebr == 0:
        s2, r2 = 20, "No EMI obligations detected"
    elif ebr <= 20:
        s2, r2 = 18, f"Low EMI burden: {ebr:.1f}% of income"
    elif ebr <= 35:
        s2, r2 = 13, f"Moderate EMI burden: {ebr:.1f}% of income"
    elif ebr <= 50:
        s2, r2 = 7,  f"High EMI burden: {ebr:.1f}% of income — repayment risk"
    elif ebr <= 65:
        s2, r2 = 3,  f"Very high EMI burden: {ebr:.1f}% — potential distress"
    else:
        s2, r2 = 0,  f"Critical EMI burden: {ebr:.1f}% — likely over-leveraged"

    components.append(ScorecardComponent("EMI Burden", s2, 20, 0.20, r2))

    # ── 3. Savings Behaviour (20 pts) ────────────────────────────────────────
    sr = insights.savings_rate
    if sr >= 30:
        s3, r3 = 20, f"Excellent savings rate: {sr:.1f}%"
    elif sr >= 20:
        s3, r3 = 16, f"Good savings rate: {sr:.1f}%"
    elif sr >= 10:
        s3, r3 = 11, f"Moderate savings: {sr:.1f}%"
    elif sr >= 0:
        s3, r3 = 6,  f"Low savings rate: {sr:.1f}% — limited buffer"
    else:
        s3, r3 = 0,  f"Negative savings: {sr:.1f}% — spending exceeds income"

    components.append(ScorecardComponent("Savings Behaviour", s3, 20, 0.20, r3))

    # ── 4. Balance Consistency (15 pts) ──────────────────────────────────────
    avg_bal = insights.avg_balance
    if avg_bal >= 50000:
        s4, r4 = 15, f"Strong avg balance: ₹{avg_bal:,.0f}"
    elif avg_bal >= 20000:
        s4, r4 = 12, f"Healthy avg balance: ₹{avg_bal:,.0f}"
    elif avg_bal >= 5000:
        s4, r4 = 8,  f"Adequate avg balance: ₹{avg_bal:,.0f}"
    elif avg_bal > 0:
        s4, r4 = 4,  f"Low avg balance: ₹{avg_bal:,.0f}"
    else:
        s4, r4 = 6,  "Balance data unavailable — neutral score applied"

    components.append(ScorecardComponent("Balance Consistency", s4, 15, 0.15, r4))

    # ── 5. Bounce / Risk Signals (10 pts) ────────────────────────────────────
    n_months = max(insights.months_analyzed, 1)
    bounce_rate = insights.bounce_count / n_months
    neg_count   = len(insights.negative_balance_months)

    s5 = 10
    reasons5 = []
    if insights.bounce_count > 0:
        deduct = min(int(bounce_rate * 20), 8)
        s5 -= deduct
        reasons5.append(f"{insights.bounce_count} low-balance month(s)")
    if neg_count > 0:
        s5 = max(0, s5 - 5)
        reasons5.append(f"{neg_count} negative balance month(s)")

    r5 = "; ".join(reasons5) if reasons5 else "No bounce or low-balance signals"
    s5 = max(0, s5)
    components.append(ScorecardComponent("Risk Signals", s5, 10, 0.10, r5))

    # ── 6. Income Level (10 pts) ──────────────────────────────────────────────
    ami = insights.avg_monthly_income
    if ami >= 100000:
        s6, r6 = 10, f"High income: avg ₹{ami:,.0f}/month"
    elif ami >= 50000:
        s6, r6 = 8,  f"Good income: avg ₹{ami:,.0f}/month"
    elif ami >= 25000:
        s6, r6 = 6,  f"Moderate income: avg ₹{ami:,.0f}/month"
    elif ami >= 10000:
        s6, r6 = 4,  f"Low income: avg ₹{ami:,.0f}/month"
    else:
        s6, r6 = 1,  f"Very low income: avg ₹{ami:,.0f}/month"

    components.append(ScorecardComponent("Income Level", s6, 10, 0.10, r6))

    # ── Final score ───────────────────────────────────────────────────────────
    total_pts = s1 + s2 + s3 + s4 + s5 + s6   # max = 100
    final_score = min(100, max(0, total_pts))

    # Risk band
    if final_score >= 80:
        risk_band = "EXCELLENT"
        recommendation = "Strong loan candidate. High confidence in repayment."
    elif final_score >= 65:
        risk_band = "GOOD"
        recommendation = "Eligible for standard loan products. Low risk."
    elif final_score >= 50:
        risk_band = "FAIR"
        recommendation = "Conditional eligibility. Recommend collateral or co-applicant."
    elif final_score >= 35:
        risk_band = "POOR"
        recommendation = "High risk. Recommend smaller loan amount with strict terms."
    else:
        risk_band = "VERY_POOR"
        recommendation = "Not recommended for loan at this time. Significant financial instability."

    summary = (
        f"Score: {final_score}/100 ({risk_band}) | "
        f"Income: ₹{insights.avg_monthly_income:,.0f}/mo | "
        f"EMI burden: {insights.emi_burden_ratio:.1f}% | "
        f"Savings: {insights.savings_rate:.1f}%"
    )

    return UnderwrightingScorecard(
        final_score=final_score,
        risk_band=risk_band,
        loan_recommendation=recommendation,
        components=[asdict(c) for c in components],
        summary=summary,
    )
