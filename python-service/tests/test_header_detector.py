import unittest

import pandas as pd

from bank_parser.processors.header_detector import find_header_row, split_header_and_data


class HeaderDetectorTestCase(unittest.TestCase):
    def test_find_header_row_prefers_keyword_heavy_row(self):
        df = pd.DataFrame(
            [
                ["Bank statement", "", "", ""],
                ["Prepared for customer", "", "", ""],
                ["Date", "Description", "Debit", "Balance"],
                ["01/01/2025", "ATM", "100.00", "900.00"],
            ]
        )

        self.assertEqual(find_header_row(df), 2)

    def test_split_header_and_data_removes_repeated_headers_and_footer_rows(self):
        df = pd.DataFrame(
            [
                ["Statement for Jan", "", "", ""],
                ["Transaction\nDate", "Description", "Debit", "Balance"],
                ["01/01/2025", "ATM cash", "100.00", "900.00"],
                ["Date", "Description", "Debit", "Balance"],
                ["02/01/2025", "Salary", "", "1900.00"],
                ["Grand Total", "", "", ""],
            ]
        )

        clean_df, raw_cols = split_header_and_data(df)

        self.assertEqual(raw_cols, ["transaction date", "description", "debit", "balance"])
        self.assertEqual(list(clean_df.columns), raw_cols)
        self.assertEqual(len(clean_df), 2)
        self.assertEqual(clean_df.iloc[0]["description"], "ATM cash")
        self.assertEqual(clean_df.iloc[1]["description"], "Salary")


if __name__ == "__main__":
    unittest.main()
