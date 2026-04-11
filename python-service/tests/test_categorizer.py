import unittest

import pandas as pd

from bank_parser.semantic.categorizer import categorize, categorize_dataframe


class CategorizerTestCase(unittest.TestCase):
    def test_categorize_respects_direction_specific_rules(self):
        self.assertEqual(categorize("Salary from ACME", credit=50000.0), "SALARY")
        self.assertEqual(categorize("Salary from ACME", debit=50000.0), "OTHER")
        self.assertEqual(categorize("UPI payment to merchant", debit=500.0), "TRANSFER_UPI")

    def test_categorize_dataframe_adds_category_column(self):
        df = pd.DataFrame(
            [
                {"Description": "Swiggy order", "Debit": 250.0, "Credit": 0.0},
                {"Description": "NEFT-SAL COMPANY", "Debit": 0.0, "Credit": 35000.0},
                {"Description": "Unknown memo", "Debit": 10.0, "Credit": 0.0},
            ]
        )

        categorized = categorize_dataframe(df)

        self.assertEqual(categorized["Category"].tolist(), ["FOOD", "SALARY", "OTHER"])
        self.assertNotIn("Category", df.columns)


if __name__ == "__main__":
    unittest.main()
