"""
Flask microservice — bank statement parser API.
Supports PDF, XLSX, XLS, ODS, CSV. Handles password-protected files.
"""

import os, sys, tempfile, traceback, json, math

SERVICE_DIR = os.path.dirname(os.path.abspath(__file__))
PARSER_DIR  = os.path.join(SERVICE_DIR, 'bank_parser')
for p in [PARSER_DIR, SERVICE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from flask import Flask, request, Response
from flask_cors import CORS
import fitz

app = Flask(__name__)
CORS(app)
UPLOAD_DIR = tempfile.mkdtemp()

SUPPORTED_EXTENSIONS = {'.pdf', '.xlsx', '.xls', '.ods', '.csv'}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024   # 50 MB

try:
    from pipeline import parse_bank_statement
    from extractor.excel_engine import is_spreadsheet, check_spreadsheet_encrypted
    from semantic.bank_detector import get_supported_banks
    print("[Parser] All imports OK", flush=True)
except Exception as e:
    print(f"[Parser] Import error: {e}", flush=True)
    traceback.print_exc()


#  Helpers

def _is_pdf_encrypted(path):
    try:
        doc = fitz.open(path)
        enc = doc.is_encrypted
        doc.close()
        return enc
    except:
        return False

def _check_pdf_password(path, pwd):
    try:
        doc = fitz.open(path)
        ok = doc.authenticate(pwd) != 0 if doc.is_encrypted else True
        doc.close()
        return ok
    except:
        return False

def _decrypt_pdf(path, pwd):
    doc = fitz.open(path)
    doc.authenticate(pwd)
    out = path + "_dec.pdf"
    doc.save(out, encryption=fitz.PDF_ENCRYPT_NONE)
    doc.close()
    return out

def _json(data, status=200):
    """Always-valid JSON response (never NaN)."""
    return Response(
        json.dumps(data, ensure_ascii=False, allow_nan=False),
        status=status,
        mimetype='application/json'
    )

def _safe_val(v):
    """Convert NaN/NaT to None for JSON serialization."""
    if v is None:
        return None
    try:
        if isinstance(v, float) and math.isnan(v):
            return None
    except:
        pass
    return v


#  Routes 

@app.route('/health', methods=['GET'])
def health():
    return _json({"status": "ok", "service": "bank-parser"})


@app.route('/supported-banks', methods=['GET'])
def supported_banks():
    """Return the list of bank codes the parser can identify."""
    try:
        banks = get_supported_banks()
    except Exception:
        banks = []
    return _json({"banks": banks, "count": len(banks)})


@app.route('/parse', methods=['POST'])
def parse():
    try:
        password = request.form.get('password', '').strip()
        file_key = request.form.get('file_key', '').strip()

        #  Resolve file 
        if 'file' in request.files and request.files['file'].filename:
            f = request.files['file']
            safe = ''.join(c for c in (f.filename or 'stmt') if c.isalnum() or c in '._-')
            tmp = os.path.join(UPLOAD_DIR, safe)
            f.save(tmp)
            file_size = os.path.getsize(tmp)
            print(f"[/parse] Saved {tmp} ({file_size} bytes)", flush=True)
            if file_size > MAX_UPLOAD_BYTES:
                os.remove(tmp)
                return _json({"status": "error",
                              "message": f"File too large ({file_size // (1024*1024)} MB). Maximum allowed is 50 MB."}, 413)
        elif file_key:
            tmp = os.path.join(UPLOAD_DIR, file_key)
            if not os.path.exists(tmp):
                return _json({"status": "error", "message": "File not found, re-upload."}, 404)
        else:
            return _json({"status": "error", "message": "No file provided."}, 400)

        ext = os.path.splitext(tmp)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return _json({"status": "error",
                          "message": f"Unsupported file type: {ext}. Use PDF, XLSX, XLS, ODS, or CSV."}, 400)

        # Encryption check 
        if ext == '.pdf':
            if _is_pdf_encrypted(tmp):
                print("[/parse] PDF encrypted", flush=True)
                if not password:
                    return _json({"status": "password_required",
                                  "file_key": os.path.basename(tmp)})
                if not _check_pdf_password(tmp, password):
                    return _json({"status": "wrong_password",
                                  "file_key": os.path.basename(tmp),
                                  "message": "Incorrect password."})
                parse_path = _decrypt_pdf(tmp, password)
            else:
                parse_path = tmp
        elif ext == '.xlsx':
            if check_spreadsheet_encrypted(tmp):
                print("[/parse] XLSX encrypted", flush=True)
                if not password:
                    return _json({"status": "password_required",
                                  "file_key": os.path.basename(tmp)})
                parse_path = tmp  # pass password to engine
            else:
                parse_path = tmp
                password = None
        else:
            parse_path = tmp
            password = None

        # Parse
        print(f"[/parse] Parsing: {parse_path}", flush=True)
        result = parse_bank_statement(parse_path, password=password if ext != '.pdf' else None)

        # Password required signal from spreadsheet engine
        if result.get("status") == "password_required":
            return _json({"status": "password_required",
                          "file_key": os.path.basename(tmp)})

        df     = result['dataframe']
        report = result['validation']

        if df.empty:
            return _json({"status": "error",
                          "message": "No transactions extracted from this file."})

        # Serialise
        df_copy = df.copy()
        df_copy['Date'] = df_copy['Date'].astype(str).replace('NaT', '')
        records_json = df_copy.to_json(orient='records', date_format='iso', force_ascii=False)
        transactions = json.loads(records_json)

        payload = {
            "status":       "success",
            "file_key":     os.path.basename(tmp),
            "file_type":    ext.lstrip('.').upper(),
            "meta": {
                "bank":               result['bank'],
                "engine":             result['engine_used'],
                "total_rows":         int(report.total_rows),
                "confidence":         float(report.confidence_score),
                "balance_mismatches": int(len(report.balance_mismatches)),
                "passed":             bool(report.passed),
                "debit_total":        float(df['Debit'].sum()),
                "credit_total":       float(df['Credit'].sum()),
            },
            "transactions": transactions,
            "insights":     result.get('insights', {}),
            "scorecard":    result.get('scorecard', {}),
        }

        return Response(
            json.dumps(payload, ensure_ascii=False, allow_nan=False),
            mimetype='application/json'
        )

    except Exception as e:
        print(f"[/parse] EXCEPTION: {e}", flush=True)
        traceback.print_exc()
        return _json({"status": "error", "message": str(e)}, 500)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    print(f"[Parser] Starting on :{port}", flush=True)
    app.run(host='0.0.0.0', port=port, debug=False)
