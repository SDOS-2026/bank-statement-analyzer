import unittest

import pandas as pd

from bank_parser.analytics.insights import (
    compute_insights,
    compute_scorecard,
    detect_emis,
)


class InsightsTestCase(unittest.TestCase):
    def test_detect_emis_finds_monthly_recurring_debits(self):
        df = pd.DataFrame(
            [
                {"Date": "2025-01-05", "Description": "NACH HOME LOAN EMI", "Debit": 5000.0},
                {"Date": "2025-02-05", "Description": "NACH HOME LOAN EMI", "Debit": 5000.0},
                {"Date": "2025-03-05", "Description": "NACH HOME LOAN EMI", "Debit": 5000.0},
                {"Date": "2025-03-20", "Description": "Groceries", "Debit": 750.0},
            ]
        )
        df["Date"] = pd.to_datetime(df["Date"])

        emis = detect_emis(df)

        self.assertEqual(len(emis), 1)
        self.assertEqual(emis[0]["frequency"], "monthly")
        self.assertEqual(emis[0]["occurrences"], 3)
        self.assertEqual(emis[0]["amount"], 5000.0)
        self.assertGreaterEqual(emis[0]["confidence"], 0.85)

    def test_compute_insights_builds_expected_totals_and_risk_flags(self):
        df = pd.DataFrame(
            [
                {
                    "Date": "2025-01-01",
                    "Description": "Salary credit",
                    "Debit": 0.0,
                    "Credit": 10000.0,
                    "Balance": 10000.0,
                    "Category": "SALARY",
                },
                {
                    "Date": "2025-01-05",
                    "Description": "Rent payment",
                    "Debit": 4000.0,
                    "Credit": 0.0,
                    "Balance": 6000.0,
                    "Category": "RENT",
                },
                {
                    "Date": "2025-01-10",
                    "Description": "EMI debit",
                    "Debit": 1000.0,
                    "Credit": 0.0,
                    "Balance": 500.0,
                    "Category": "EMI",
                },
                {
                    "Date": "2025-02-01",
                    "Description": "Salary credit",
                    "Debit": 0.0,
                    "Credit": 12000.0,
                    "Balance": 12500.0,
                    "Category": "SALARY",
                },
                {
                    "Date": "2025-02-02",
                    "Description": "Online shopping",
                    "Debit": 3000.0,
                    "Credit": 0.0,
                    "Balance": 9500.0,
                    "Category": "SHOPPING",
                },
                {
                    "Date": "2025-02-15",
                    "Description": "Utility bill",
                    "Debit": 1000.0,
                    "Credit": 0.0,
                    "Balance": -100.0,
                    "Category": "UTILITIES",
                },
            ]
        )

        insights = compute_insights(df)

        self.assertEqual(insights.period_start, "2025-01-01")
        self.assertEqual(insights.period_end, "2025-02-15")
        self.assertEqual(insights.months_analyzed, 2)
        self.assertEqual(insights.total_income, 22000.0)
        self.assertEqual(insights.total_expenses, 9000.0)
        self.assertEqual(insights.total_emi, 1000.0)
        self.assertEqual(insights.net_savings, 13000.0)
        self.assertEqual(insights.bounce_count, 1)
        self.assertEqual(insights.low_balance_months, ["2025-01"])
        self.assertEqual(insights.negative_balance_months, ["2025-02"])
        self.assertEqual(insights.category_totals["EMI"], 1000.0)
        self.assertEqual(insights.category_totals["RENT"], 4000.0)
        self.assertEqual(insights.category_totals["SHOPPING"], 3000.0)
        self.assertEqual(insights.monthly_breakdown[0]["month"], "2025-01")
        self.assertEqual(insights.monthly_breakdown[0]["income"], 10000.0)
        self.assertEqual(insights.monthly_breakdown[1]["month"], "2025-02")
        self.assertEqual(insights.monthly_breakdown[1]["expenses"], 4000.0)

    def test_compute_scorecard_assigns_excellent_band_for_strong_profile(self):
        df = pd.DataFrame(
            [
                {
                    "Date": "2025-01-01",
                    "Description": "Salary",
                    "Debit": 0.0,
                    "Credit": 100000.0,
                    "Balance": 100000.0,
                    "Category": "SALARY",
                },
                {
                    "Date": "2025-01-05",
                    "Description": "Investments",
                    "Debit": 20000.0,
                    "Credit": 0.0,
                    "Balance": 80000.0,
                    "Category": "INVESTMENT",
                },
                {
                    "Date": "2025-02-01",
                    "Description": "Salary",
                    "Debit": 0.0,
                    "Credit": 100000.0,
                    "Balance": 180000.0,
                    "Category": "SALARY",
                },
                {
                    "Date": "2025-02-04",
                    "Description": "Rent",
                    "Debit": 20000.0,
                    "Credit": 0.0,
                    "Balance": 160000.0,
                    "Category": "RENT",
                },
                {
                    "Date": "2025-03-01",
                    "Description": "Salary",
                    "Debit": 0.0,
                    "Credit": 100000.0,
                    "Balance": 260000.0,
                    "Category": "SALARY",
                },
                {
                    "Date": "2025-03-04",
                    "Description": "Travel",
                    "Debit": 10000.0,
                    "Credit": 0.0,
                    "Balance": 250000.0,
                    "Category": "TRAVEL",
                },
            ]
        )

        scorecard = compute_scorecard(compute_insights(df))

        self.assertGreaterEqual(scorecard.final_score, 80)
        self.assertEqual(scorecard.risk_band, "EXCELLENT")
        self.assertIn("Strong loan candidate", scorecard.loan_recommendation)


if __name__ == "__main__":
    unittest.main()
