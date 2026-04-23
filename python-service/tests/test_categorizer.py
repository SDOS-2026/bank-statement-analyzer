import unittest
import pandas as pd

from bank_parser.semantic.categorizer import categorize, categorize_dataframe


class CategorizerTestCase(unittest.TestCase):

    # ----------------------------
    # Core behavior tests
    # ----------------------------
    def test_categorize_respects_direction_specific_rules(self):
        self.assertEqual(categorize("Salary from ACME", credit=50000.0), "SALARY")
        self.assertEqual(categorize("Salary from ACME", debit=50000.0), "OTHER")
        self.assertEqual(categorize("UPI payment to merchant", debit=500.0), "TRANSFER_UPI")

    def test_categorize_is_case_insensitive(self):
        self.assertEqual(categorize("salary from acme", credit=1000), "SALARY")
        self.assertEqual(categorize("SwIgGy order", debit=200), "FOOD")

    def test_categorize_unknown_defaults_to_other(self):
        self.assertEqual(categorize("Random unknown text", debit=100), "OTHER")

    def test_categorize_empty_description(self):
        self.assertEqual(categorize("", debit=100), "OTHER")

    # ----------------------------
    # Input validation tests
    # ----------------------------
    def test_categorize_both_credit_and_debit_zero(self):
        self.assertEqual(categorize("Salary from ACME", credit=0.0, debit=0.0), "OTHER")

    def test_categorize_both_credit_and_debit_nonzero(self):
        # Depending on your design, this might raise an error instead
        result = categorize("Salary from ACME", credit=1000.0, debit=1000.0)
        self.assertIn(result, ["SALARY", "OTHER"])  # flexible but safe

    def test_categorize_handles_nan(self):
        self.assertEqual(categorize("Salary from ACME", credit=float("nan")), "OTHER")

    # ----------------------------
    # DataFrame behavior tests
    # ----------------------------
    def test_categorize_dataframe_adds_category_column(self):
        df = pd.DataFrame(
            [
                {"Description": "Swiggy order", "Debit": 250.0, "Credit": 0.0},
                {"Description": "NEFT-SAL COMPANY", "Debit": 0.0, "Credit": 35000.0},
                {"Description": "Unknown memo", "Debit": 10.0, "Credit": 0.0},
            ]
        )

        categorized = categorize_dataframe(df)

        self.assertEqual(
            categorized["Category"].tolist(),
            ["FOOD", "SALARY", "OTHER"]
        )

    def test_categorize_dataframe_does_not_mutate_original(self):
        df = pd.DataFrame(
            [{"Description": "Test", "Debit": 100.0, "Credit": 0.0}]
        )
        original_df = df.copy(deep=True)

        _ = categorize_dataframe(df)

        pd.testing.assert_frame_equal(df, original_df)

    def test_categorize_dataframe_handles_missing_values(self):
        df = pd.DataFrame(
            [
                {"Description": None, "Debit": 100.0, "Credit": 0.0},
                {"Description": "Salary", "Debit": None, "Credit": 5000.0},
            ]
        )

        categorized = categorize_dataframe(df)

        self.assertEqual(len(categorized), 2)
        self.assertIn("Category", categorized.columns)

    def test_categorize_dataframe_missing_columns_raises(self):
        df = pd.DataFrame(
            [{"Desc": "Test", "Amount": 100}]
        )

        with self.assertRaises(Exception):
            categorize_dataframe(df)


if __name__ == "__main__":
    unittest.main()