import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


SERVICE_DIR = Path(__file__).resolve().parents[1]
BANK_PARSER_DIR = SERVICE_DIR / "bank_parser"
sys.path.insert(0, str(BANK_PARSER_DIR))

from analytics.underwriting import _principal_from_emi, compute_scorecard


def insights(**overrides):
    base = {
        "period_start": "2025-01-01",
        "period_end": "2025-06-30",
        "months_analyzed": 6,
        "total_income": 600000,
        "total_expenses": 330000,
        "total_emi": 30000,
        "net_savings": 270000,
        "avg_monthly_income": 100000,
        "avg_monthly_expenses": 55000,
        "avg_monthly_savings": 45000,
        "avg_balance": 180000,
        "savings_rate": 45.0,
        "emi_burden_ratio": 5.0,
        "detected_emis": [],
        "emi_count": 0,
        "income_stability_score": 0.95,
        "income_months": 6,
        "bounce_count": 0,
        "low_balance_months": [],
        "negative_balance_months": [],
        "category_totals": {},
        "top_expense_categories": [],
        "monthly_breakdown": [],
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class UnderwritingPolicyTests(unittest.TestCase):
    def test_high_quality_cashflow_gets_product_recommendations(self):
        scorecard = compute_scorecard(insights())
        self.assertEqual(scorecard.decision, "APPROVE")
        self.assertGreaterEqual(scorecard.final_score, 80)
        self.assertGreater(scorecard.max_recommended_loan_amount, 0)
        eligible = [p for p in scorecard.recommended_products if p["status"] == "ELIGIBLE"]
        self.assertTrue(any(p["product_type"] == "PERSONAL_LOAN" for p in eligible))

    def test_high_existing_emi_limits_new_credit(self):
        scorecard = compute_scorecard(insights(
            avg_monthly_income=60000,
            avg_monthly_expenses=59000,
            savings_rate=1.7,
            emi_burden_ratio=62.0,
            avg_balance=8000,
        ))
        self.assertNotEqual(scorecard.decision, "APPROVE")
        self.assertIn("Existing EMI burden is too high", scorecard.adverse_action_reasons)
        self.assertEqual(scorecard.max_recommended_loan_amount, 0.0)

    def test_insufficient_history_requires_review_or_decline(self):
        scorecard = compute_scorecard(insights(
            months_analyzed=2,
            income_months=2,
            income_stability_score=0.50,
        ))
        self.assertIn("Insufficient statement history", scorecard.adverse_action_reasons)
        self.assertFalse(any(p["status"] == "ELIGIBLE" for p in scorecard.recommended_products))

    def test_negative_cashflow_blocks_affordability(self):
        scorecard = compute_scorecard(insights(
            avg_monthly_income=45000,
            avg_monthly_expenses=60000,
            savings_rate=-33.3,
            avg_balance=3000,
        ))
        self.assertIn("Negative monthly cashflow", scorecard.adverse_action_reasons)
        self.assertEqual(scorecard.max_recommended_loan_amount, 0.0)

    def test_present_value_formula_for_affordable_principal(self):
        principal = _principal_from_emi(10000, 12.0, 12)
        self.assertAlmostEqual(principal, 112550.78, delta=1.0)

    def test_secured_product_can_be_conditional_when_score_is_borderline(self):
        scorecard = compute_scorecard(insights(
            avg_monthly_income=55000,
            avg_monthly_expenses=40000,
            avg_monthly_savings=15000,
            savings_rate=27.2,
            avg_balance=32000,
            income_stability_score=0.68,
            emi_burden_ratio=8.0,
        ))

        two_wheeler = next(
            p for p in scorecard.recommended_products
            if p["product_type"] == "TWO_WHEELER_LOAN"
        )
        self.assertIn(two_wheeler["status"], {"ELIGIBLE", "CONDITIONAL"})
        self.assertGreater(two_wheeler["max_amount"], 0)

    def test_negative_balance_blocks_unsecured_credit_but_keeps_reasons_auditable(self):
        scorecard = compute_scorecard(insights(
            negative_balance_months=["2026-01"],
            bounce_count=1,
            avg_monthly_income=90000,
            avg_monthly_expenses=50000,
            savings_rate=44.4,
            avg_balance=70000,
        ))
        personal_loan = next(
            p for p in scorecard.recommended_products
            if p["product_type"] == "PERSONAL_LOAN"
        )

        self.assertEqual(personal_loan["status"], "NOT_ELIGIBLE")
        self.assertIn("Negative balance history is not acceptable for unsecured credit", personal_loan["reasons"])
        self.assertIn("Negative account balance observed", scorecard.adverse_action_reasons)

    def test_scorecard_summary_exposes_policy_version_and_assumptions(self):
        scorecard = compute_scorecard(insights())

        self.assertEqual(scorecard.policy_version, "statement-underwriting-v1.0")
        self.assertTrue(scorecard.summary.startswith("Score:"))
        self.assertGreaterEqual(len(scorecard.assumptions), 3)


if __name__ == "__main__":
    unittest.main()
