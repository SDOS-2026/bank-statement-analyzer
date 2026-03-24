"""
Fixed app.py - key change: use pandas .to_json() for NaN→null serialization
instead of manual record building which produces invalid JSON NaN literals.
"""

import os, sys, tempfile, traceback, json

SERVICE_DIR = os.path.dirname(os.path.abspath(__file__))
PARSER_DIR  = os.path.join(SERVICE_DIR, 'bank_parser')
for p in [PARSER_DIR, SERVICE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import fitz

app = Flask(__name__)
CORS(app)

UPLOAD_DIR = tempfile.mkdtemp()
print(f"[Parser] Upload dir: {UPLOAD_DIR}", flush=True)
print(f"[Parser] SERVICE_DIR: {SERVICE_DIR}", flush=True)

try:
    from pipeline import parse_bank_statement
    print("[Parser] Pipeline import OK", flush=True)
except Exception as e:
    print(f"[Parser] WARNING pipeline import failed: {e}", flush=True)
    traceback.print_exc()


# ── Helpers ───────────────────────────────────────────────────────────────────

def is_encrypted(path):
    try:
        doc = fitz.open(path)
        enc = doc.is_encrypted
        doc.close()
        return enc
    except:
        return False

def check_password(path, pwd):
    try:
        doc = fitz.open(path)
        if doc.is_encrypted:
            ok = doc.authenticate(pwd) != 0
            doc.close()
            return ok
        doc.close()
        return True
    except:
        return False

def decrypt_to_temp(path, pwd):
    doc = fitz.open(path)
    doc.authenticate(pwd)
    out = path + "_dec.pdf"
    doc.save(out, encryption=fitz.PDF_ENCRYPT_NONE)
    doc.close()
    return out


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "bank-parser"})


@app.route('/parse', methods=['POST'])
def parse():
    try:
        password = request.form.get('password', '').strip()
        file_key = request.form.get('file_key', '').strip()

        print(f"[/parse] file={bool('file' in request.files and request.files['file'].filename)} key='{file_key}' pwd={bool(password)}", flush=True)

        # ── Resolve file ──────────────────────────────────────────────────────
        if 'file' in request.files and request.files['file'].filename:
            f = request.files['file']
            safe = ''.join(c for c in (f.filename or 'stmt.pdf') if c.isalnum() or c in '._-')
            tmp = os.path.join(UPLOAD_DIR, safe)
            f.save(tmp)
            print(f"[/parse] Saved {tmp} ({os.path.getsize(tmp)} bytes)", flush=True)
        elif file_key:
            tmp = os.path.join(UPLOAD_DIR, file_key)
            if not os.path.exists(tmp):
                return _json({"status": "error", "message": "File not found, please re-upload."}, 404)
            print(f"[/parse] Reusing {tmp}", flush=True)
        else:
            return _json({"status": "error", "message": "No file provided."}, 400)

        # ── Encryption check ──────────────────────────────────────────────────
        if is_encrypted(tmp):
            print("[/parse] PDF is encrypted", flush=True)
            if not password:
                return _json({"status": "password_required", "file_key": os.path.basename(tmp)})
            if not check_password(tmp, password):
                return _json({"status": "wrong_password",
                               "file_key": os.path.basename(tmp),
                               "message": "Incorrect password. Please try again."})
            parse_path = decrypt_to_temp(tmp, password)
        else:
            parse_path = tmp

        # ── Parse ─────────────────────────────────────────────────────────────
        print(f"[/parse] Parsing {parse_path}", flush=True)
        from pipeline import parse_bank_statement
        result = parse_bank_statement(parse_path)

        df     = result['dataframe']
        report = result['validation']

        print(f"[/parse] rows={len(df)} confidence={report.confidence_score}", flush=True)

        if df.empty:
            return _json({"status": "error", "message": "No transactions extracted from this PDF."})

        # ── Serialise: use pandas to_json so NaN → null (valid JSON) ─────────
        # orient='records' gives [{col:val,...}, ...]
        # date_format='iso' keeps dates as strings
        # force_ascii=False keeps unicode (₹ etc)
        transactions_json_str = df.to_json(orient='records', date_format='iso', force_ascii=False)
        transactions = json.loads(transactions_json_str)   # now NaN is null ✓

        payload = {
            "status": "success",
            "file_key": os.path.basename(tmp),
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
            "transactions": transactions
        }

        # Use json.dumps with ensure_ascii=False so response is clean JSON
        return Response(
            json.dumps(payload, ensure_ascii=False, allow_nan=False),
            mimetype='application/json'
        )

    except Exception as e:
        print(f"[/parse] EXCEPTION: {e}", flush=True)
        traceback.print_exc()
        return _json({"status": "error", "message": str(e)}, 500)


def _json(data, status=200):
    """Safe JSON response that never produces NaN literals."""
    return Response(
        json.dumps(data, ensure_ascii=False, allow_nan=False),
        status=status,
        mimetype='application/json'
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    print(f"[Parser] Starting on :{port}", flush=True)
    app.run(host='0.0.0.0', port=port, debug=False)
