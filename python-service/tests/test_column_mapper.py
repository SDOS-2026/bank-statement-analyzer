import sys
import unittest
from pathlib import Path

import pandas as pd


SERVICE_DIR = Path(__file__).resolve().parents[1]
BANK_PARSER_DIR = SERVICE_DIR / "bank_parser"
sys.path.insert(0, str(BANK_PARSER_DIR))

from semantic.column_mapper import apply_column_mapping, clean_balance_cr_dr, map_columns


class ColumnMapperTests(unittest.TestCase):
    def test_maps_bank_specific_headers_to_standard_schema(self):
        mapping = map_columns([
            "Txn Date",
            "Transaction Remarks",
            "Withdrawal Amount",
            "Deposit Amount",
            "Running Balance",
            "Chq / Ref No.",
        ])

        self.assertEqual(mapping["Txn Date"], "Date")
        self.assertEqual(mapping["Transaction Remarks"], "Description")
        self.assertEqual(mapping["Withdrawal Amount"], "Debit")
        self.assertEqual(mapping["Deposit Amount"], "Credit")
        self.assertEqual(mapping["Running Balance"], "Balance")
        self.assertEqual(mapping["Chq / Ref No."], "Reference")

    def test_splits_combined_amount_and_transaction_type_columns(self):
        df = pd.DataFrame([
            {"Date": "2026-01-01", "Narration": "ATM", "Amount": "1,500.00", "Dr/Cr": "DR", "Balance": "8,500.00"},
            {"Date": "2026-01-02", "Narration": "Salary", "Amount": "75,000.00", "Dr/Cr": "CR", "Balance": "83,500.00"},
        ])

        mapped = apply_column_mapping(df)

        self.assertEqual(mapped.loc[0, "Debit"], 1500.0)
        self.assertTrue(pd.isna(mapped.loc[0, "Credit"]))
        self.assertTrue(pd.isna(mapped.loc[1, "Debit"]))
        self.assertEqual(mapped.loc[1, "Credit"], 75000.0)
        self.assertEqual(list(mapped.columns), ["Date", "Description", "Debit", "Credit", "Balance", "Reference"])

    def test_splits_inline_dr_cr_amount_column(self):
        df = pd.DataFrame([
            {"Date": "2026-02-01", "Description": "Bill pay", "Amount": "2,400.50 DR", "Balance": "10,000.00"},
            {"Date": "2026-02-02", "Description": "Refund", "Amount": "400.00 CR", "Balance": "10,400.00"},
        ])

        mapped = apply_column_mapping(df)

        self.assertEqual(mapped.loc[0, "Debit"], 2400.50)
        self.assertEqual(mapped.loc[1, "Credit"], 400.0)

    def test_infers_missing_date_column_from_date_like_values(self):
        df = pd.DataFrame([
            {"Posting": "01/03/2026", "Narration": "Opening", "Debit": "-", "Credit": "-", "Balance": "5000"},
            {"Posting": "02/03/2026", "Narration": "Coffee", "Debit": "120", "Credit": "-", "Balance": "4880"},
        ])

        mapped = apply_column_mapping(df)

        self.assertEqual(mapped.loc[0, "Date"], "01/03/2026")
        self.assertEqual(mapped.loc[1, "Description"], "Coffee")

    def test_clean_balance_cr_dr_handles_overdrawn_balances(self):
        self.assertEqual(clean_balance_cr_dr("15,234.50 CR"), 15234.50)
        self.assertEqual(clean_balance_cr_dr("500.00 DR"), -500.0)
        self.assertIsNone(clean_balance_cr_dr("-"))


if __name__ == "__main__":
    unittest.main()
