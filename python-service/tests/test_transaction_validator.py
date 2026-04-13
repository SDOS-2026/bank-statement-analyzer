import unittest

import pandas as pd

from bank_parser.validators.transaction_validator import validate


class TransactionValidatorTestCase(unittest.TestCase):
    def test_validate_flags_balance_mismatches_and_suspicious_rows(self):
        df = pd.DataFrame(
            [
                {"Date": "2025-01-01", "Description": "Opening", "Debit": 0.0, "Credit": 0.0, "Balance": 1000.0},
                {"Date": "2025-01-02", "Description": "ATM", "Debit": 100.0, "Credit": 0.0, "Balance": 900.0},
                {"Date": "2025-01-03", "Description": "", "Debit": 50.0, "Credit": 100.0, "Balance": 850.0},
                {"Date": None, "Description": "Rent", "Debit": 200.0, "Credit": 0.0, "Balance": 650.0},
                {"Date": "2025-01-05", "Description": "Mismatch", "Debit": 100.0, "Credit": 0.0, "Balance": 700.0},
            ]
        )

        report = validate(df)

        self.assertEqual(report.total_rows, 5)
        self.assertEqual(report.valid_rows, 3)
        self.assertEqual(report.missing_dates, 1)
        self.assertEqual(report.missing_descriptions, 1)
        self.assertEqual(report.balance_mismatches, [2, 4])
        self.assertEqual(report.suspicious_rows, [2])
        self.assertFalse(report.passed)
        self.assertTrue(any("both Debit and Credit" in note for note in report.notes))

    def test_validate_empty_dataframe_returns_early_with_note(self):
        report = validate(pd.DataFrame(columns=["Date", "Description", "Debit", "Credit", "Balance"]))

        self.assertEqual(report.total_rows, 0)
        self.assertFalse(report.passed)
        self.assertIn("DataFrame is empty.", report.notes)


if __name__ == "__main__":
    unittest.main()
