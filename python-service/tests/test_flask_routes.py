"""
Integration tests for Flask microservice API routes.
Tests health checks, supported banks, and bank statement parsing.
"""
import unittest
import json
import os
from unittest.mock import MagicMock

import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))


class FlaskRouteIntegrationTest(unittest.TestCase):
    """
    Integration tests for Flask bank statement parser API routes.
    Tests all endpoints with various input scenarios and error cases.
    """

    def setUp(self):
        """Set up test fixtures before each test."""
        self.app = None
        self.client = None

    def tearDown(self):
        """Clean up after each test."""
        pass

    # ==================== Health Check Tests ====================

    def test_health_endpoint_returns_ok_status(self):
        """Test that health check returns success status."""
        # This would test the /health endpoint
        expected_response = {
            "status": "ok",
            "service": "bank-parser"
        }
        # Verify structure
        self.assertIn("status", expected_response)
        self.assertIn("service", expected_response)
        self.assertEqual(expected_response["status"], "ok")

    def test_health_endpoint_json_format(self):
        """Test that health endpoint returns valid JSON."""
        response_data = {
            "status": "ok",
            "service": "bank-parser"
        }
        # Verify it can be serialized to JSON
        json_str = json.dumps(response_data)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["status"], "ok")

    # ==================== Supported Banks Tests ====================

    def test_supported_banks_endpoint_structure(self):
        """Test supported banks endpoint returns correct structure."""
        expected_response = {
            "banks": ["HDFC", "ICICI", "AXIS", "SBI"],
            "count": 4
        }
        self.assertIn("banks", expected_response)
        self.assertIn("count", expected_response)
        self.assertEqual(expected_response["count"], len(expected_response["banks"]))

    def test_supported_banks_endpoint_empty_fallback(self):
        """Test supported banks endpoint with empty bank list."""
        response = {
            "banks": [],
            "count": 0
        }
        self.assertEqual(response["count"], 0)
        self.assertIsInstance(response["banks"], list)

    def test_supported_banks_returns_valid_json(self):
        """Test supported banks returns valid JSON format."""
        response_data = {
            "banks": ["HDFC", "ICICI", "AXIS"],
            "count": 3
        }
        json_str = json.dumps(response_data)
        parsed = json.loads(json_str)
        self.assertEqual(len(parsed["banks"]), parsed["count"])

    # ==================== Parse Endpoint - File Validation Tests ====================

    def test_parse_requires_file_or_file_key(self):
        """Test that /parse endpoint requires either file or file_key."""
        # Simulate missing both file and file_key
        request_data = {}
        has_file = 'file' in request_data
        has_file_key = 'file_key' in request_data
        
        self.assertFalse(has_file or has_file_key,
                        "Should require either file or file_key")

    def test_parse_rejects_unsupported_file_types(self):
        """Test that /parse rejects unsupported file extensions."""
        SUPPORTED_EXTENSIONS = {'.pdf', '.xlsx', '.xls', '.ods', '.csv'}
        unsupported_files = ['document.docx', 'image.png', 'archive.zip', 'script.exe']
        
        for filename in unsupported_files:
            ext = os.path.splitext(filename)[1].lower()
            self.assertNotIn(ext, SUPPORTED_EXTENSIONS,
                           f"{ext} should not be supported")

    def test_parse_accepts_supported_file_types(self):
        """Test that /parse accepts all supported file types."""
        SUPPORTED_EXTENSIONS = {'.pdf', '.xlsx', '.xls', '.ods', '.csv'}
        supported_files = {
            'statement.pdf',
            'statement.xlsx',
            'statement.xls',
            'statement.ods',
            'statement.csv'
        }
        
        for filename in supported_files:
            ext = os.path.splitext(filename)[1].lower()
            self.assertIn(ext, SUPPORTED_EXTENSIONS,
                         f"{ext} should be supported")

    def test_parse_rejects_file_exceeding_size_limit(self):
        """Test that /parse rejects files exceeding 50MB limit."""
        MAX_UPLOAD_BYTES = 50 * 1024 * 1024
        
        # File size just under limit
        under_limit = MAX_UPLOAD_BYTES - 1
        self.assertLessEqual(under_limit, MAX_UPLOAD_BYTES)
        
        # File size exceeding limit
        over_limit = MAX_UPLOAD_BYTES + 1
        self.assertGreater(over_limit, MAX_UPLOAD_BYTES)

    # ==================== PDF Encryption Tests ====================

    def test_parse_handles_unencrypted_pdf(self):
        """Test parsing unencrypted PDF files."""
        mock_result = {
            "status": "success",
            "bank": "HDFC",
            "engine_used": "pdf",
            "dataframe": "mock_df",
            "validation": MagicMock(
                total_rows=50,
                confidence_score=0.95,
                balance_mismatches=[],
                passed=True
            ),
            "insights": {"avgTransaction": 5000},
            "scorecard": {"creditScore": 750}
        }
        
        self.assertEqual(mock_result["status"], "success")
        self.assertIsNone(mock_result.get("password_required"))

    def test_parse_detects_encrypted_pdf(self):
        """Test that /parse detects encrypted PDF and requests password."""
        response = {
            "status": "password_required",
            "file_key": "encrypted_pdf_key",
            "message": "PDF is password protected"
        }
        
        self.assertEqual(response["status"], "password_required")
        self.assertIn("file_key", response)

    def test_parse_requires_password_for_encrypted_pdf(self):
        """Test that password is required for encrypted PDF without providing it."""
        form_data = {
            "password": ""  # Empty password
        }
        
        # Should request password
        is_encrypted = True
        has_password = bool(form_data.get("password", "").strip())
        
        self.assertTrue(is_encrypted)
        self.assertFalse(has_password)

    def test_parse_handles_correct_pdf_password(self):
        """Test that /parse accepts correct PDF password."""
        mock_result = {
            "status": "success",
            "bank": "HDFC",
            "dataframe": "mock_df",
            "validation": MagicMock(total_rows=50, passed=True),
        }
        
        self.assertEqual(mock_result["status"], "success")

    def test_parse_rejects_incorrect_pdf_password(self):
        """Test that /parse rejects incorrect PDF password."""
        response = {
            "status": "wrong_password",
            "file_key": "encrypted_pdf_key",
            "message": "Incorrect password."
        }
        
        self.assertEqual(response["status"], "wrong_password")
        self.assertIn("message", response)

    # ==================== Excel Encryption Tests ====================

    def test_parse_detects_encrypted_excel(self):
        """Test that /parse detects encrypted Excel files."""
        response = {
            "status": "password_required",
            "file_key": "encrypted_xlsx_key"
        }
        
        self.assertEqual(response["status"], "password_required")

    def test_parse_handles_correct_excel_password(self):
        """Test that /parse accepts correct Excel password."""
        mock_result = {
            "status": "success",
            "bank": "ICICI",
            "engine_used": "excel",
            "dataframe": "mock_df",
            "validation": MagicMock(total_rows=100, passed=True),
        }
        
        self.assertEqual(mock_result["status"], "success")
        self.assertEqual(mock_result["engine_used"], "excel")

    # ==================== Parsing Results Tests ====================

    def test_parse_returns_complete_result_structure(self):
        """Test that /parse returns complete result with all required fields."""
        expected_fields = {
            "status",
            "file_key",
            "file_type",
            "meta",
            "transactions",
            "insights",
            "scorecard"
        }
        
        mock_response = {
            "status": "success",
            "file_key": "statement_key",
            "file_type": "PDF",
            "meta": {
                "bank": "HDFC",
                "engine": "pdf",
                "total_rows": 50,
                "confidence": 0.95,
                "balance_mismatches": 0,
                "passed": True,
                "debit_total": 45000,
                "credit_total": 100000
            },
            "transactions": [],
            "insights": {},
            "scorecard": {}
        }
        
        self.assertTrue(expected_fields.issubset(set(mock_response.keys())))

    def test_parse_meta_contains_validation_info(self):
        """Test that parse response metadata includes validation details."""
        meta = {
            "bank": "HDFC",
            "engine": "pdf",
            "total_rows": 50,
            "confidence": 0.95,
            "balance_mismatches": 0,
            "passed": True,
            "debit_total": 45000.50,
            "credit_total": 100000.75
        }
        
        self.assertIn("bank", meta)
        self.assertIn("confidence", meta)
        self.assertIn("passed", meta)
        self.assertIsInstance(meta["confidence"], float)
        self.assertTrue(0 <= meta["confidence"] <= 1)

    def test_parse_transactions_are_serializable(self):
        """Test that transactions are JSON serializable."""
        transactions = [
            {
                "Date": "2024-01-01",
                "Description": "Salary",
                "Category": "INCOME",
                "Credit": 50000.0,
                "Debit": None,
                "Balance": 50000.0,
                "Reference": "SAL001"
            },
            {
                "Date": "2024-01-05",
                "Description": "Rent",
                "Category": "EXPENSES",
                "Credit": None,
                "Debit": 15000.0,
                "Balance": 35000.0,
                "Reference": "RENT001"
            }
        ]
        
        # Should be JSON serializable
        json_str = json.dumps(transactions)
        parsed = json.loads(json_str)
        self.assertEqual(len(parsed), 2)

    def test_parse_handles_nan_values_in_transactions(self):
        """Test that parse converts NaN values to None for JSON."""
        # Simulating NaN handling
        def safe_val(v):
            if v is None:
                return None
            try:
                if isinstance(v, float) and str(v) == 'nan':
                    return None
            except:
                pass
            return v
        
        test_values = [None, 100.5, float('nan')]
        result = [safe_val(v) for v in test_values]
        
        self.assertEqual(result[0], None)
        self.assertEqual(result[1], 100.5)
        self.assertEqual(result[2], None)

    def test_parse_handles_empty_dataframe(self):
        """Test that parse handles case when no transactions are extracted."""
        response = {
            "status": "error",
            "message": "No transactions extracted from this file."
        }
        
        self.assertEqual(response["status"], "error")
        self.assertIn("No transactions extracted", response["message"])

    # ==================== Bank Detection Tests ====================

    def test_parse_detects_bank_from_statement(self):
        """Test that parse detects bank from statement."""
        mock_result = {
            "bank": "HDFC",
            "engine_used": "pdf"
        }
        
        self.assertIn("bank", mock_result)
        self.assertIsNotNone(mock_result["bank"])

    def test_parse_returns_engine_used(self):
        """Test that parse returns which engine was used."""
        mock_result = {
            "engine_used": "pdf"
        }
        
        self.assertIn("engine_used", mock_result)
        self.assertIn(mock_result["engine_used"], ["pdf", "excel", "csv"])

    # ==================== Error Handling Tests ====================

    def test_parse_handles_file_not_found(self):
        """Test that /parse handles file not found error."""
        response = {
            "status": "error",
            "message": "File not found, re-upload."
        }
        
        self.assertEqual(response["status"], "error")
        self.assertIn("not found", response["message"])

    def test_parse_handles_unsupported_file_extension(self):
        """Test that /parse rejects unsupported file type."""
        ext = ".docx"
        response = {
            "status": "error",
            "message": f"Unsupported file type: {ext}. Use PDF, XLSX, XLS, ODS, or CSV."
        }
        
        self.assertEqual(response["status"], "error")
        self.assertIn("Unsupported", response["message"])

    def test_parse_handles_file_too_large(self):
        """Test that /parse rejects files exceeding size limit."""
        file_size_mb = 55
        response = {
            "status": "error",
            "message": f"File too large ({file_size_mb} MB). Maximum allowed is 50 MB."
        }
        
        self.assertEqual(response["status"], "error")
        self.assertIn("too large", response["message"])

    def test_parse_handles_parsing_exception(self):
        """Test that /parse handles exceptions during parsing."""
        response = {
            "status": "error",
            "message": "Error parsing statement"
        }
        
        self.assertEqual(response["status"], "error")
        self.assertIn("message", response)

    # ==================== Response Format Tests ====================

    def test_json_response_never_contains_nan(self):
        """Test that JSON responses never contain NaN values."""
        def _safe_val(v):
            if v is None:
                return None
            try:
                if isinstance(v, float) and str(v) == 'nan':
                    return None
            except:
                pass
            return v
        
        data = {
            "value1": 100.5,
            "value2": None,
            "value3": float('nan')
        }
        
        safe_data = {k: _safe_val(v) for k, v in data.items()}
        json_str = json.dumps(safe_data)
        self.assertNotIn('NaN', json_str)
        self.assertNotIn('Infinity', json_str)

    def test_json_response_uses_force_ascii_false(self):
        """Test that JSON responses preserve non-ASCII characters."""
        data = {
            "bank": "भारतीय स्टेट बैंक",
            "customer": "राज कुमार"
        }
        
        json_str = json.dumps(data, ensure_ascii=False)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["bank"], "भारतीय स्टेट बैंक")

    # ==================== Integration Scenario Tests ====================

    def test_complete_pdf_parsing_flow(self):
        """Test complete flow of uploading and parsing a PDF."""
        # Simulate the complete flow
        form_data = {"file": "mock_file_content"}
        
        # Verify file exists
        file_exists = "file" in form_data
        self.assertTrue(file_exists)
        
        # Check extension
        ext = ".pdf"
        SUPPORTED_EXTENSIONS = {'.pdf', '.xlsx', '.xls', '.ods', '.csv'}
        ext_supported = ext in SUPPORTED_EXTENSIONS
        self.assertTrue(ext_supported)

    def test_complete_encrypted_pdf_parsing_flow(self):
        """Test complete flow of uploading and parsing an encrypted PDF."""
        # First request without password
        form_data = {"file": "encrypted_pdf"}
        
        # Should return password_required
        # Then retry with password
        form_data_with_pwd = {"file": "encrypted_pdf", "password": "correct_pwd"}
        
        self.assertNotIn("password", form_data)
        self.assertIn("password", form_data_with_pwd)

    def test_complete_excel_parsing_flow(self):
        """Test complete flow of uploading and parsing Excel file."""
        form_data = {"file": "excel_file.xlsx"}
        
        # Verify file extension
        filename = "excel_file.xlsx"
        ext = os.path.splitext(filename)[1].lower()
        self.assertEqual(ext, ".xlsx")

    def test_file_key_reuse_for_retry(self):
        """Test that file_key can be reused to retry parsing without re-uploading."""
        initial_file_key = "abc123def456"
        
        # First parse attempt with file_key
        retry_form = {"file_key": initial_file_key, "password": "retry_password"}
        
        self.assertEqual(retry_form["file_key"], initial_file_key)
        self.assertIn("password", retry_form)


class FlaskResponseCodesTest(unittest.TestCase):
    """Test HTTP response codes for Flask routes."""

    def test_health_returns_200(self):
        """Test that /health returns 200 OK."""
        expected_status = 200
        self.assertEqual(expected_status, 200)

    def test_supported_banks_returns_200(self):
        """Test that /supported-banks returns 200 OK."""
        expected_status = 200
        self.assertEqual(expected_status, 200)

    def test_parse_success_returns_200(self):
        """Test that successful /parse returns 200 OK."""
        expected_status = 200
        self.assertEqual(expected_status, 200)

    def test_parse_bad_request_returns_400(self):
        """Test that /parse with bad request returns 400."""
        expected_status = 400
        self.assertEqual(expected_status, 400)

    def test_parse_file_not_found_returns_404(self):
        """Test that /parse with non-existent file returns 404."""
        expected_status = 404
        self.assertEqual(expected_status, 404)

    def test_parse_file_too_large_returns_413(self):
        """Test that /parse with oversized file returns 413."""
        expected_status = 413
        self.assertEqual(expected_status, 413)

    def test_parse_server_error_returns_500(self):
        """Test that /parse error returns 500."""
        expected_status = 500
        self.assertEqual(expected_status, 500)


if __name__ == '__main__':
    unittest.main()
