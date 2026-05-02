import sys
import unittest
from pathlib import Path

import pandas as pd


SERVICE_DIR = Path(__file__).resolve().parents[1]
BANK_PARSER_DIR = SERVICE_DIR / "bank_parser"
sys.path.insert(0, str(BANK_PARSER_DIR))

from analytics.insights import compute_insights, detect_emis


class FinancialInsightsTests(unittest.TestCase):
    def test_compute_insights_builds_monthly_cashflow_and_risk_signals(self):
        df = pd.DataFrame([
            {"Date": "2026-01-01", "Description": "Salary", "Credit": 100000, "Debit": None, "Balance": 100000, "Category": "SALARY"},
            {"Date": "2026-01-05", "Description": "Rent", "Credit": None, "Debit": 30000, "Balance": 70000, "Category": "RENT"},
            {"Date": "2026-01-10", "Description": "EMI", "Credit": None, "Debit": 12000, "Balance": 58000, "Category": "EMI"},
            {"Date": "2026-02-01", "Description": "Salary", "Credit": 105000, "Debit": None, "Balance": 105000, "Category": "SALARY"},
            {"Date": "2026-02-15", "Description": "Medical", "Credit": None, "Debit": 104500, "Balance": 500, "Category": "HEALTHCARE"},
            {"Date": "2026-03-01", "Description": "Salary", "Credit": 95000, "Debit": None, "Balance": 95500, "Category": "SALARY"},
            {"Date": "2026-03-20", "Description": "Tax", "Credit": None, "Debit": 97000, "Balance": -1500, "Category": "TAXES"},
        ])

        insights = compute_insights(df)

        self.assertEqual(insights.months_analyzed, 3)
        self.assertEqual(insights.income_months, 3)
        self.assertEqual(insights.total_income, 300000)
        self.assertEqual(insights.total_emi, 12000)
        self.assertEqual(insights.emi_burden_ratio, 4.0)
        self.assertEqual(insights.low_balance_months, ["2026-02"])
        self.assertEqual(insights.negative_balance_months, ["2026-03"])
        self.assertEqual(insights.bounce_count, 1)
        self.assertEqual(len(insights.monthly_breakdown), 3)
        self.assertEqual(insights.top_expense_categories[0]["category"], "HEALTHCARE")

    def test_detect_emis_finds_recurring_monthly_fixed_debits(self):
        df = pd.DataFrame([
            {"Date": "2026-01-05", "Description": "NACH Loan EMI", "Debit": 15000.0},
            {"Date": "2026-02-05", "Description": "NACH Loan EMI", "Debit": 15000.0},
            {"Date": "2026-03-06", "Description": "NACH Loan EMI", "Debit": 15020.0},
            {"Date": "2026-03-10", "Description": "Groceries", "Debit": 3200.0},
        ])
        df["Date"] = pd.to_datetime(df["Date"])

        emis = detect_emis(df)

        self.assertEqual(len(emis), 1)
        self.assertEqual(emis[0]["frequency"], "monthly")
        self.assertEqual(emis[0]["occurrences"], 3)
        self.assertGreaterEqual(emis[0]["confidence"], 0.85)

    def test_empty_dataframe_returns_zeroed_insights(self):
        insights = compute_insights(pd.DataFrame())

        self.assertEqual(insights.months_analyzed, 0)
        self.assertEqual(insights.total_income, 0)
        self.assertEqual(insights.detected_emis, [])
        self.assertEqual(insights.monthly_breakdown, [])


if __name__ == "__main__":
    unittest.main()
