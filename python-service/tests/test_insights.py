import unittest
import pandas as pd

from bank_parser.analytics.insights import (
    compute_insights,
    compute_scorecard,
    detect_emis,
)


class InsightsTestCase(unittest.TestCase):

    # ----------------------------
    # Helpers
    # ----------------------------
    def _to_datetime(self, df):
        df = df.copy()
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        return df

    # ----------------------------
    # detect_emis tests
    # ----------------------------
    def test_detect_emis_finds_monthly_recurring_debits(self):
        df = pd.DataFrame(
            [
                {"Date": "2025-01-05", "Description": "NACH HOME LOAN EMI", "Debit": 5000.0},
                {"Date": "2025-02-05", "Description": "NACH HOME LOAN EMI", "Debit": 5000.0},
                {"Date": "2025-03-05", "Description": "NACH HOME LOAN EMI", "Debit": 5000.0},
                {"Date": "2025-03-20", "Description": "Groceries", "Debit": 750.0},
            ]
        )
        df = self._to_datetime(df)

        emis = detect_emis(df)

        self.assertEqual(len(emis), 1)

        emi = emis[0]
        self.assertEqual(emi["frequency"], "monthly")
        self.assertEqual(emi["occurrences"], 3)
        self.assertAlmostEqual(emi["amount"], 5000.0)
        self.assertGreaterEqual(emi["confidence"], 0.85)

    def test_detect_emis_handles_no_patterns(self):
        df = pd.DataFrame(
            [
                {"Date": "2025-01-01", "Description": "Food", "Debit": 200},
                {"Date": "2025-01-10", "Description": "Shopping", "Debit": 500},
            ]
        )
        df = self._to_datetime(df)

        emis = detect_emis(df)
        self.assertEqual(emis, [])

    def test_detect_emis_ignores_credits(self):
        df = pd.DataFrame(
            [
                {"Date": "2025-01-05", "Description": "EMI", "Credit": 5000.0},
                {"Date": "2025-02-05", "Description": "EMI", "Credit": 5000.0},
            ]
        )
        df = self._to_datetime(df)

        emis = detect_emis(df)
        self.assertEqual(emis, [])

    # ----------------------------
    # compute_insights tests
    # ----------------------------
    def test_compute_insights_builds_expected_totals_and_flags(self):
        df = pd.DataFrame(
            [
                {"Date": "2025-01-01", "Description": "Salary", "Debit": 0.0, "Credit": 10000.0, "Balance": 10000.0, "Category": "SALARY"},
                {"Date": "2025-01-05", "Description": "Rent", "Debit": 4000.0, "Credit": 0.0, "Balance": 6000.0, "Category": "RENT"},
                {"Date": "2025-01-10", "Description": "EMI", "Debit": 1000.0, "Credit": 0.0, "Balance": 500.0, "Category": "EMI"},
                {"Date": "2025-02-01", "Description": "Salary", "Debit": 0.0, "Credit": 12000.0, "Balance": 12500.0, "Category": "SALARY"},
                {"Date": "2025-02-02", "Description": "Shopping", "Debit": 3000.0, "Credit": 0.0, "Balance": 9500.0, "Category": "SHOPPING"},
                {"Date": "2025-02-15", "Description": "Utility", "Debit": 1000.0, "Credit": 0.0, "Balance": -100.0, "Category": "UTILITIES"},
            ]
        )
        df = self._to_datetime(df)

        insights = compute_insights(df)

        self.assertEqual(insights.period_start, "2025-01-01")
        self.assertEqual(insights.period_end, "2025-02-15")
        self.assertEqual(insights.months_analyzed, 2)

        self.assertAlmostEqual(insights.total_income, 22000.0)
        self.assertAlmostEqual(insights.total_expenses, 9000.0)
        self.assertAlmostEqual(insights.total_emi, 1000.0)
        self.assertAlmostEqual(insights.net_savings, 13000.0)

        self.assertEqual(insights.bounce_count, 1)
        self.assertIn("2025-01", insights.low_balance_months)
        self.assertIn("2025-02", insights.negative_balance_months)

        self.assertEqual(insights.category_totals["EMI"], 1000.0)
        self.assertEqual(insights.category_totals["RENT"], 4000.0)

        # Order-independent checks
        months = {m["month"]: m for m in insights.monthly_breakdown}
        self.assertEqual(months["2025-01"]["income"], 10000.0)
        self.assertEqual(months["2025-02"]["expenses"], 4000.0)

    def test_compute_insights_handles_empty_dataframe(self):
        df = pd.DataFrame(columns=["Date", "Debit", "Credit", "Balance", "Category"])

        insights = compute_insights(df)

        self.assertEqual(insights.total_income, 0.0)
        self.assertEqual(insights.total_expenses, 0.0)
        self.assertEqual(insights.months_analyzed, 0)

    def test_compute_insights_does_not_mutate_input(self):
        df = pd.DataFrame(
            [{"Date": "2025-01-01", "Debit": 0.0, "Credit": 100.0, "Balance": 100.0, "Category": "SALARY"}]
        )
        df = self._to_datetime(df)

        original = df.copy(deep=True)
        _ = compute_insights(df)

        pd.testing.assert_frame_equal(df, original)

    # ----------------------------
    # compute_scorecard tests
    # ----------------------------
    def test_compute_scorecard_assigns_excellent_band(self):
        df = pd.DataFrame(
            [
                {"Date": "2025-01-01", "Debit": 0.0, "Credit": 100000.0, "Balance": 100000.0, "Category": "SALARY"},
                {"Date": "2025-01-05", "Debit": 20000.0, "Credit": 0.0, "Balance": 80000.0, "Category": "INVESTMENT"},
                {"Date": "2025-02-01", "Debit": 0.0, "Credit": 100000.0, "Balance": 180000.0, "Category": "SALARY"},
                {"Date": "2025-02-04", "Debit": 20000.0, "Credit": 0.0, "Balance": 160000.0, "Category": "RENT"},
                {"Date": "2025-03-01", "Debit": 0.0, "Credit": 100000.0, "Balance": 260000.0, "Category": "SALARY"},
                {"Date": "2025-03-04", "Debit": 10000.0, "Credit": 0.0, "Balance": 250000.0, "Category": "TRAVEL"},
            ]
        )
        df = self._to_datetime(df)

        scorecard = compute_scorecard(compute_insights(df))

        self.assertGreaterEqual(scorecard.final_score, 80)
        self.assertEqual(scorecard.risk_band, "EXCELLENT")
        self.assertTrue("loan" in scorecard.loan_recommendation.lower())

    def test_compute_scorecard_handles_poor_profile(self):
        df = pd.DataFrame(
            [
                {"Date": "2025-01-01", "Debit": 5000.0, "Credit": 0.0, "Balance": -500.0, "Category": "EXPENSE"},
            ]
        )
        df = self._to_datetime(df)

        scorecard = compute_scorecard(compute_insights(df))

        self.assertLess(scorecard.final_score, 50)


if __name__ == "__main__":
    unittest.main()