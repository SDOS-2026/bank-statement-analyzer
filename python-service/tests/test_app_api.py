import io
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd


SERVICE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_DIR))

import app as parser_app  # noqa: E402


class ParserApiIntegrationTests(unittest.TestCase):
    def setUp(self):
        parser_app.app.config["TESTING"] = True
        self.upload_dir = SERVICE_DIR / "tests" / "tmp_uploads"
        self.upload_dir.mkdir(exist_ok=True)
        parser_app.UPLOAD_DIR = str(self.upload_dir)
        self.client = parser_app.app.test_client()

    def tearDown(self):
        for path in self.upload_dir.glob("*"):
            if path.is_file():
                try:
                    path.unlink()
                except PermissionError:
                    pass

    def test_health_endpoint(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")
        self.assertEqual(response.get_json()["service"], "bank-parser")

    def test_parse_requires_a_file(self):
        response = self.client.post("/parse", data={})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["status"], "error")
        self.assertIn("No file provided", response.get_json()["message"])

    def test_parse_rejects_unsupported_extensions(self):
        response = self.client.post(
            "/parse",
            data={"file": (io.BytesIO(b"not a statement"), "statement.txt")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["status"], "error")
        self.assertIn("Unsupported file type", response.get_json()["message"])

    def test_parse_returns_serialized_transactions_for_successful_csv(self):
        dataframe = pd.DataFrame([
            {
                "Date": pd.Timestamp("2026-01-01"),
                "Description": "Salary",
                "Debit": 0.0,
                "Credit": 90000.0,
                "Balance": 120000.0,
                "Reference": "NEFT123",
                "Category": "Income",
            }
        ])
        validation = SimpleNamespace(
            total_rows=1,
            confidence_score=0.98,
            balance_mismatches=[],
            passed=True,
        )
        parse_result = {
            "dataframe": dataframe,
            "validation": validation,
            "bank": "HDFC",
            "engine_used": "csv",
            "insights": {"avg_monthly_income": 90000},
            "scorecard": {"final_score": 82},
        }

        with patch.object(parser_app, "parse_bank_statement", return_value=parse_result) as parse_bank_statement:
            response = self.client.post(
                "/parse",
                data={"file": (io.BytesIO(b"csv data"), "statement.csv")},
                content_type="multipart/form-data",
            )

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["file_type"], "CSV")
        self.assertEqual(payload["meta"]["bank"], "HDFC")
        self.assertEqual(payload["meta"]["total_rows"], 1)
        self.assertEqual(payload["transactions"][0]["Description"], "Salary")
        self.assertEqual(payload["transactions"][0]["Credit"], 90000.0)
        parse_bank_statement.assert_called_once()


if __name__ == "__main__":
    unittest.main()
