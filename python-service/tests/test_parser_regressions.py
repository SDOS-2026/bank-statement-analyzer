import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


SERVICE_DIR = Path(__file__).resolve().parents[1]
BANK_PARSER_DIR = SERVICE_DIR / "bank_parser"
sys.path.insert(0, str(BANK_PARSER_DIR))

from extractor.engine_runner import _build_rows_from_text
from pipeline import parse_bank_statement
from semantic.bank_detector import detect_bank, normalize_bank_name
from validators.transaction_validator import validate


SAMPLES_DIR = SERVICE_DIR.parent / "sample_statements"


class ParserRegressionTests(unittest.TestCase):
    def test_normalize_compact_bank_names(self):
        self.assertEqual(normalize_bank_name("indianbank"), "INDIAN_BANK")
        self.assertEqual(normalize_bank_name("punjabandsindbank"), "PUNJAB_SIND")
        self.assertEqual(normalize_bank_name("ucobank"), "UCO")

    def test_sample_bank_detection_priority_and_filename_fallbacks(self):
        cases = {
            "axis.pdf": "AXIS",
            "paytm.pdf": "PAYTM",
            "pnb.pdf": "PNB",
            "ucobank.pdf": "UCO",
        }
        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                path = SAMPLES_DIR / filename
                if not path.exists():
                    self.skipTest(f"sample missing: {filename}")
                self.assertEqual(detect_bank(str(path)), expected)

    def test_encrypted_pdf_returns_password_required(self):
        path = SAMPLES_DIR / "pnb.pdf"
        if not path.exists():
            self.skipTest("pnb sample missing")
        result = parse_bank_statement(str(path))
        self.assertEqual(result["status"], "password_required")
        self.assertFalse(result["success"])

    def test_text_rows_use_full_date_not_serial_number(self):
        text = "\n".join([
            "Transaction                                    Withdrawal Deposit Balance",
            "S No.         Cheque Number    Transaction Remarks",
            "       Date                                         Amount (INR) Amount (INR) (INR)",
            "    1   02.11.2025                                         260.00          492.27 ",
            "                          UPI/merchant/a",
            "    2   02.11.2025                                                   10.22 502.49 ",
            "                          UPI/refund/b",
        ])
        rows = _build_rows_from_text(text)
        self.assertEqual(rows[0]["Date"], "02.11.2025")
        self.assertEqual(rows[0]["Debit"], 260.0)
        self.assertIsNone(rows[0]["Credit"])
        self.assertEqual(rows[1]["Credit"], 10.22)
        self.assertEqual(rows[1]["Balance"], 502.49)

    def test_text_rows_parse_cr_suffix_running_balance(self):
        text = "\n".join([
            "Value  Post  Details  Chq.No.  Debit      Credit      Balance",
            "07/05/24 07/05/24 TO TRF.  .    -           2,071.00                      4,30,303.60Cr",
            ".         .  UPI RRN 449489799840                .         .",
            ".         .  TRF TO 51427049828 .",
        ])
        rows = _build_rows_from_text(text)
        self.assertEqual(rows[0]["Debit"], 2071.0)
        self.assertIsNone(rows[0]["Credit"])
        self.assertEqual(rows[0]["Balance"], 430303.60)

    def test_validation_treats_nan_amounts_as_zero(self):
        df = pd.DataFrame([
            {"Date": "2026-01-01", "Description": "opening", "Debit": np.nan, "Credit": np.nan, "Balance": 100.0},
            {"Date": "2026-01-02", "Description": "bad row", "Debit": np.nan, "Credit": np.nan, "Balance": 110.0},
            {"Date": "2026-01-03", "Description": "normal debit", "Debit": 10.0, "Credit": np.nan, "Balance": 100.0},
            {"Date": "2026-01-04", "Description": "normal credit", "Debit": np.nan, "Credit": 20.0, "Balance": 120.0},
        ])
        report = validate(df)
        self.assertEqual(report.balance_mismatches, [1])
        self.assertLess(report.confidence_score, 1.0)

    def test_validation_accepts_reverse_chronological_statements(self):
        df = pd.DataFrame([
            {"Date": "2026-01-03", "Description": "latest debit", "Debit": 100.0, "Credit": np.nan, "Balance": 400.0},
            {"Date": "2026-01-02", "Description": "previous credit", "Debit": np.nan, "Credit": 200.0, "Balance": 500.0},
            {"Date": "2026-01-01", "Description": "older debit", "Debit": 50.0, "Credit": np.nan, "Balance": 300.0},
            {"Date": "2025-12-31", "Description": "opening-ish", "Debit": np.nan, "Credit": np.nan, "Balance": 350.0},
        ])
        report = validate(df)
        self.assertEqual(report.balance_mismatches, [])
        self.assertIn("reverse-chronological", " ".join(report.notes))


if __name__ == "__main__":
    unittest.main()
