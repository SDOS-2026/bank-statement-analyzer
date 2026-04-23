import unittest
import pandas as pd

from bank_parser.processors.header_detector import (
    find_header_row,
    split_header_and_data,
)


class HeaderDetectorTestCase(unittest.TestCase):

    # ----------------------------
    # find_header_row tests
    # ----------------------------
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

    def test_find_header_row_handles_case_and_noise(self):
        df = pd.DataFrame(
            [
                ["random text", "", "", ""],
                ["dAtE", "DesCription", "debit", "BALANCE"],
                ["01/01/2025", "ATM", "100.00", "900.00"],
            ]
        )

        self.assertEqual(find_header_row(df), 1)

    def test_find_header_row_with_multiple_candidates(self):
        df = pd.DataFrame(
            [
                ["Date", "Desc", "", ""],  # partial header
                ["Transaction Date", "Description", "Debit", "Balance"],  # better match
                ["01/01/2025", "ATM", "100.00", "900.00"],
            ]
        )

        self.assertEqual(find_header_row(df), 1)

    def test_find_header_row_returns_none_if_not_found(self):
        df = pd.DataFrame(
            [
                ["random", "text", "", ""],
                ["more", "noise", "", ""],
            ]
        )

        result = find_header_row(df)
        self.assertIn(result, [None, -1])  # depending on implementation

    # ----------------------------
    # split_header_and_data tests
    # ----------------------------
    def test_split_header_and_data_basic(self):
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

        self.assertEqual(
            raw_cols,
            ["transaction date", "description", "debit", "balance"]
        )
        self.assertEqual(list(clean_df.columns), raw_cols)
        self.assertEqual(len(clean_df), 2)
        self.assertEqual(clean_df.iloc[0]["description"], "ATM cash")
        self.assertEqual(clean_df.iloc[1]["description"], "Salary")

    def test_split_header_removes_repeated_headers(self):
        df = pd.DataFrame(
            [
                ["Date", "Description", "Debit", "Balance"],
                ["01/01/2025", "ATM", "100", "900"],
                ["Date", "Description", "Debit", "Balance"],
                ["02/01/2025", "Food", "200", "700"],
            ]
        )

        clean_df, _ = split_header_and_data(df)

        self.assertEqual(len(clean_df), 2)

    def test_split_header_removes_footer_rows(self):
        df = pd.DataFrame(
            [
                ["Date", "Description", "Debit", "Balance"],
                ["01/01/2025", "ATM", "100", "900"],
                ["Total", "", "", ""],
                ["Closing Balance", "", "", ""],
            ]
        )

        clean_df, _ = split_header_and_data(df)

        self.assertEqual(len(clean_df), 1)
        self.assertEqual(clean_df.iloc[0]["description"], "ATM")

    def test_split_handles_missing_values(self):
        df = pd.DataFrame(
            [
                ["Date", "Description", "Debit", "Balance"],
                ["01/01/2025", None, "100", "900"],
                ["02/01/2025", "Salary", None, "1900"],
            ]
        )

        clean_df, _ = split_header_and_data(df)

        self.assertEqual(len(clean_df), 2)

    def test_split_normalizes_column_names(self):
        df = pd.DataFrame(
            [
                ["DATE", "DESCRIPTION", "DEBIT", "BALANCE"],
                ["01/01/2025", "ATM", "100", "900"],
            ]
        )

        _, raw_cols = split_header_and_data(df)

        self.assertEqual(
            raw_cols,
            ["date", "description", "debit", "balance"]
        )

    def test_split_does_not_mutate_original_dataframe(self):
        df = pd.DataFrame(
            [
                ["Date", "Description", "Debit", "Balance"],
                ["01/01/2025", "ATM", "100", "900"],
            ]
        )

        original_df = df.copy(deep=True)

        _ = split_header_and_data(df)

        pd.testing.assert_frame_equal(df, original_df)

    def test_split_raises_on_missing_header(self):
        df = pd.DataFrame(
            [
                ["random", "text", "", ""],
                ["no", "header", "", ""],
            ]
        )

        with self.assertRaises(Exception):
            split_header_and_data(df)


if __name__ == "__main__":
    unittest.main()