"""
Policy-driven underwriting from bank-statement insights.

This module is intentionally deterministic. It is not a black-box model and it
does not make a legally final credit decision. It produces an auditable
recommendation, affordability limits, and the concrete reasons behind the result.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import pow
from typing import Any


POLICY_VERSION = "statement-underwriting-v1.0"


@dataclass(frozen=True)
class ScorecardComponent:
    name: str
    score: int
    max_score: int
    weight: float
    reasoning: str


@dataclass(frozen=True)
class ProductPolicy:
    product_type: str
    display_name: str
    secured: bool
    min_score_approve: int
    min_score_review: int
    min_monthly_income: float
    min_statement_months: int
    max_foir_pct: float
    annual_rate_pct: float
    max_tenure_months: int
    income_multiple_cap: float
    absolute_cap: float
    min_offer_amount: float
    residual_surplus_buffer_pct: float = 65.0


@dataclass(frozen=True)
class LoanProductRecommendation:
    product_type: str
    display_name: str
    status: str
    secured: bool
    max_amount: float
    monthly_emi: float
    tenure_months: int
    indicative_apr: float
    max_foir_pct: float
    reasons: list[str]
    mitigants: list[str]


@dataclass(frozen=True)
class UnderwritingScorecard:
    final_score: int
    risk_band: str
    loan_recommendation: str
    components: list[dict]
    summary: str
    decision: str
    max_recommended_loan_amount: float
    recommended_monthly_emi: float
    recommended_products: list[dict]
    adverse_action_reasons: list[str]
    policy_version: str
    assumptions: list[str]


PRODUCT_POLICIES = [
    ProductPolicy(
        product_type="PERSONAL_LOAN",
        display_name="Unsecured personal loan",
        secured=False,
        min_score_approve=70,
        min_score_review=58,
        min_monthly_income=25000,
        min_statement_months=3,
        max_foir_pct=40,
        annual_rate_pct=16.0,
        max_tenure_months=60,
        income_multiple_cap=18,
        absolute_cap=2000000,
        min_offer_amount=25000,
    ),
    ProductPolicy(
        product_type="TWO_WHEELER_LOAN",
        display_name="Two-wheeler loan",
        secured=True,
        min_score_approve=58,
        min_score_review=48,
        min_monthly_income=12000,
        min_statement_months=3,
        max_foir_pct=45,
        annual_rate_pct=13.0,
        max_tenure_months=48,
        income_multiple_cap=10,
        absolute_cap=300000,
        min_offer_amount=20000,
    ),
    ProductPolicy(
        product_type="AUTO_LOAN",
        display_name="Vehicle loan",
        secured=True,
        min_score_approve=64,
        min_score_review=52,
        min_monthly_income=30000,
        min_statement_months=3,
        max_foir_pct=50,
        annual_rate_pct=11.0,
        max_tenure_months=84,
        income_multiple_cap=30,
        absolute_cap=5000000,
        min_offer_amount=100000,
    ),
    ProductPolicy(
        product_type="HOME_LOAN",
        display_name="Home loan",
        secured=True,
        min_score_approve=72,
        min_score_review=60,
        min_monthly_income=40000,
        min_statement_months=6,
        max_foir_pct=50,
        annual_rate_pct=9.0,
        max_tenure_months=240,
        income_multiple_cap=60,
        absolute_cap=20000000,
        min_offer_amount=500000,
        residual_surplus_buffer_pct=55.0,
    ),
    ProductPolicy(
        product_type="MSME_WORKING_CAPITAL",
        display_name="MSME working-capital term loan",
        secured=True,
        min_score_approve=68,
        min_score_review=56,
        min_monthly_income=50000,
        min_statement_months=6,
        max_foir_pct=45,
        annual_rate_pct=18.0,
        max_tenure_months=36,
        income_multiple_cap=6,
        absolute_cap=3000000,
        min_offer_amount=100000,
    ),
]


def compute_scorecard(insights: Any) -> UnderwritingScorecard:
    components = _score_components(insights)
    final_score = max(0, min(100, sum(c.score for c in components)))
    risk_band = _risk_band(final_score)
    adverse_reasons = _principal_reasons(insights, final_score)
    product_recs = [_evaluate_product(policy, insights, final_score) for policy in PRODUCT_POLICIES]

    positive_products = [p for p in product_recs if p.status in {"ELIGIBLE", "CONDITIONAL"}]
    eligible_products = [p for p in product_recs if p.status == "ELIGIBLE"]

    if eligible_products:
        decision = "APPROVE"
    elif positive_products:
        decision = "CONDITIONAL"
    elif final_score >= 50:
        decision = "MANUAL_REVIEW"
    else:
        decision = "DECLINE"

    best = max(positive_products, key=lambda p: p.max_amount, default=None)
    max_amount = round(best.max_amount, 2) if best else 0.0
    recommended_emi = round(best.monthly_emi, 2) if best else 0.0

    recommendation = _recommendation_text(decision, risk_band, best)
    summary = (
        f"Score: {final_score}/100 ({risk_band}) | "
        f"Decision: {decision} | "
        f"Income: INR {_money(getattr(insights, 'avg_monthly_income', 0))}/mo | "
        f"Existing EMI burden: {getattr(insights, 'emi_burden_ratio', 0):.1f}% | "
        f"Max recommended amount: INR {_money(max_amount)}"
    )

    return UnderwritingScorecard(
        final_score=final_score,
        risk_band=risk_band,
        loan_recommendation=recommendation,
        components=[asdict(c) for c in components],
        summary=summary,
        decision=decision,
        max_recommended_loan_amount=max_amount,
        recommended_monthly_emi=recommended_emi,
        recommended_products=[asdict(p) for p in product_recs],
        adverse_action_reasons=adverse_reasons[:4],
        policy_version=POLICY_VERSION,
        assumptions=[
            "Uses bank-statement cashflow only; bureau score, KYC, employment verification, collateral value, fraud checks, and policy exceptions must be evaluated separately.",
            "Income is treated as net observed inflow because bank statements do not reliably expose gross income.",
            "Loan amounts are indicative affordability ceilings, not sanctioned offers.",
        ],
    )


def _score_components(insights: Any) -> list[ScorecardComponent]:
    components: list[ScorecardComponent] = []

    stab = float(getattr(insights, "income_stability_score", 0) or 0)
    if stab >= 0.90:
        s1, r1 = 25, "Highly stable recurring income across the statement period"
    elif stab >= 0.75:
        s1, r1 = 20, "Mostly stable recurring income with minor variation"
    elif stab >= 0.55:
        s1, r1 = 14, "Moderate income variability detected"
    elif stab >= 0.30:
        s1, r1 = 8, "High income variability"
    else:
        s1, r1 = 3, "Very unstable or absent recurring income"

    income_months = int(getattr(insights, "income_months", 0) or 0)
    if income_months < 3:
        s1 = max(0, s1 - 8)
        r1 += f"; only {income_months} month(s) with income"
    components.append(ScorecardComponent("Income Stability", s1, 25, 0.25, r1))

    ebr = float(getattr(insights, "emi_burden_ratio", 0) or 0)
    if ebr == 0:
        s2, r2 = 20, "No existing EMI obligations detected"
    elif ebr <= 20:
        s2, r2 = 18, f"Low existing EMI burden at {ebr:.1f}% of income"
    elif ebr <= 35:
        s2, r2 = 13, f"Moderate existing EMI burden at {ebr:.1f}%"
    elif ebr <= 50:
        s2, r2 = 7, f"High existing EMI burden at {ebr:.1f}%"
    elif ebr <= 65:
        s2, r2 = 3, f"Very high existing EMI burden at {ebr:.1f}%"
    else:
        s2, r2 = 0, f"Critical existing EMI burden at {ebr:.1f}%"
    components.append(ScorecardComponent("Existing Debt Burden", s2, 20, 0.20, r2))

    sr = float(getattr(insights, "savings_rate", 0) or 0)
    if sr >= 30:
        s3, r3 = 20, f"Strong cash surplus; savings rate {sr:.1f}%"
    elif sr >= 20:
        s3, r3 = 16, f"Healthy cash surplus; savings rate {sr:.1f}%"
    elif sr >= 10:
        s3, r3 = 11, f"Moderate cash surplus; savings rate {sr:.1f}%"
    elif sr >= 0:
        s3, r3 = 6, f"Thin cash surplus; savings rate {sr:.1f}%"
    else:
        s3, r3 = 0, f"Negative cashflow; spending exceeds income by {-sr:.1f}%"
    components.append(ScorecardComponent("Cashflow Surplus", s3, 20, 0.20, r3))

    avg_bal = float(getattr(insights, "avg_balance", 0) or 0)
    income = float(getattr(insights, "avg_monthly_income", 0) or 0)
    balance_months = avg_bal / income if income > 0 else 0
    if balance_months >= 1.5:
        s4, r4 = 15, "Average balance covers at least 1.5 months of observed income"
    elif balance_months >= 0.75:
        s4, r4 = 12, "Average balance provides a meaningful liquidity buffer"
    elif avg_bal >= 5000:
        s4, r4 = 8, "Average balance is positive but liquidity buffer is modest"
    elif avg_bal > 0:
        s4, r4 = 4, "Low average balance"
    else:
        s4, r4 = 6, "Balance data unavailable; neutral liquidity score applied"
    components.append(ScorecardComponent("Liquidity Buffer", s4, 15, 0.15, r4))

    n_months = max(int(getattr(insights, "months_analyzed", 0) or 0), 1)
    bounce_count = int(getattr(insights, "bounce_count", 0) or 0)
    neg_count = len(getattr(insights, "negative_balance_months", []) or [])
    bounce_rate = bounce_count / n_months
    s5 = 10
    reasons5 = []
    if bounce_count:
        s5 -= min(int(bounce_rate * 20), 8)
        reasons5.append(f"{bounce_count} low-balance month(s)")
    if neg_count:
        s5 = max(0, s5 - 5)
        reasons5.append(f"{neg_count} negative-balance month(s)")
    components.append(ScorecardComponent(
        "Account Conduct",
        max(0, s5),
        10,
        0.10,
        "; ".join(reasons5) if reasons5 else "No low-balance or negative-balance signal detected",
    ))

    if income >= 100000:
        s6, r6 = 10, f"High observed monthly income: INR {_money(income)}"
    elif income >= 50000:
        s6, r6 = 8, f"Good observed monthly income: INR {_money(income)}"
    elif income >= 25000:
        s6, r6 = 6, f"Moderate observed monthly income: INR {_money(income)}"
    elif income >= 10000:
        s6, r6 = 4, f"Low observed monthly income: INR {_money(income)}"
    else:
        s6, r6 = 1, f"Very low observed monthly income: INR {_money(income)}"
    components.append(ScorecardComponent("Income Level", s6, 10, 0.10, r6))

    return components


def _evaluate_product(policy: ProductPolicy, insights: Any, final_score: int) -> LoanProductRecommendation:
    reasons: list[str] = []
    mitigants: list[str] = []

    income = float(getattr(insights, "avg_monthly_income", 0) or 0)
    months = int(getattr(insights, "months_analyzed", 0) or 0)
    existing_emi = income * float(getattr(insights, "emi_burden_ratio", 0) or 0) / 100.0
    avg_expenses = float(getattr(insights, "avg_monthly_expenses", 0) or 0)

    if months < policy.min_statement_months:
        reasons.append(f"Requires at least {policy.min_statement_months} months of statement history")
    if income < policy.min_monthly_income:
        reasons.append(f"Observed monthly income below {policy.display_name} minimum")
    if final_score < policy.min_score_review:
        reasons.append("Underwriting score below review floor for this product")
    elif final_score < policy.min_score_approve:
        mitigants.append("Eligible only with stronger verification, collateral, guarantor, or reduced amount")

    if getattr(insights, "negative_balance_months", None) and not policy.secured:
        reasons.append("Negative balance history is not acceptable for unsecured credit")

    foir_capacity = income * policy.max_foir_pct / 100.0 - existing_emi
    surplus = income - avg_expenses
    surplus_capacity = surplus * policy.residual_surplus_buffer_pct / 100.0
    emi_capacity = max(0.0, min(foir_capacity, surplus_capacity))

    if emi_capacity <= 0:
        reasons.append("No positive EMI capacity after existing obligations and cashflow buffer")

    amount_by_emi = _principal_from_emi(emi_capacity, policy.annual_rate_pct, policy.max_tenure_months)
    amount_by_income = income * policy.income_multiple_cap
    max_amount = max(0.0, min(amount_by_emi, amount_by_income, policy.absolute_cap))
    max_amount = _round_down(max_amount, 1000)

    if max_amount < policy.min_offer_amount:
        reasons.append("Calculated affordable amount is below the minimum useful ticket size")
        max_amount = 0.0

    status = "NOT_ELIGIBLE"
    if not reasons:
        status = "ELIGIBLE" if final_score >= policy.min_score_approve else "CONDITIONAL"

    return LoanProductRecommendation(
        product_type=policy.product_type,
        display_name=policy.display_name,
        status=status,
        secured=policy.secured,
        max_amount=round(max_amount, 2),
        monthly_emi=round(_emi_from_principal(max_amount, policy.annual_rate_pct, policy.max_tenure_months), 2),
        tenure_months=policy.max_tenure_months,
        indicative_apr=policy.annual_rate_pct,
        max_foir_pct=policy.max_foir_pct,
        reasons=reasons,
        mitigants=mitigants,
    )


def _principal_from_emi(monthly_emi: float, annual_rate_pct: float, tenure_months: int) -> float:
    if monthly_emi <= 0 or tenure_months <= 0:
        return 0.0
    monthly_rate = annual_rate_pct / 1200.0
    if monthly_rate == 0:
        return monthly_emi * tenure_months
    return monthly_emi * (1 - pow(1 + monthly_rate, -tenure_months)) / monthly_rate


def _emi_from_principal(principal: float, annual_rate_pct: float, tenure_months: int) -> float:
    if principal <= 0 or tenure_months <= 0:
        return 0.0
    monthly_rate = annual_rate_pct / 1200.0
    if monthly_rate == 0:
        return principal / tenure_months
    factor = pow(1 + monthly_rate, tenure_months)
    return principal * monthly_rate * factor / (factor - 1)


def _principal_reasons(insights: Any, final_score: int) -> list[str]:
    reasons: list[str] = []
    if int(getattr(insights, "months_analyzed", 0) or 0) < 3:
        reasons.append("Insufficient statement history")
    if int(getattr(insights, "income_months", 0) or 0) < 3:
        reasons.append("Insufficient recurring income evidence")
    if float(getattr(insights, "income_stability_score", 0) or 0) < 0.55:
        reasons.append("Unstable or irregular income pattern")
    if float(getattr(insights, "emi_burden_ratio", 0) or 0) > 50:
        reasons.append("Existing EMI burden is too high")
    if float(getattr(insights, "savings_rate", 0) or 0) < 0:
        reasons.append("Negative monthly cashflow")
    if getattr(insights, "negative_balance_months", None):
        reasons.append("Negative account balance observed")
    if int(getattr(insights, "bounce_count", 0) or 0) > 0:
        reasons.append("Low-balance account conduct observed")
    if final_score < 50:
        reasons.append("Overall statement-based score below policy threshold")
    return reasons or ["No material adverse statement-based reason identified"]


def _risk_band(score: int) -> str:
    if score >= 80:
        return "EXCELLENT"
    if score >= 65:
        return "GOOD"
    if score >= 50:
        return "FAIR"
    if score >= 35:
        return "POOR"
    return "VERY_POOR"


def _recommendation_text(decision: str, risk_band: str, best: LoanProductRecommendation | None) -> str:
    if decision == "APPROVE" and best:
        return f"Eligible for {best.display_name} up to INR {_money(best.max_amount)} subject to verification and policy checks."
    if decision == "CONDITIONAL" and best:
        return f"Conditional eligibility for {best.display_name} up to INR {_money(best.max_amount)} with additional mitigants."
    if decision == "MANUAL_REVIEW":
        return "Manual review recommended; affordability or conduct is borderline for automated policy."
    return f"Not recommended for new credit under {POLICY_VERSION}; risk band is {risk_band}."


def _round_down(value: float, nearest: int) -> float:
    if value <= 0:
        return 0.0
    return float(int(value // nearest) * nearest)


def _money(value: float) -> str:
    return f"{value:,.0f}"
