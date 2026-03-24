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


# Routes 

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "bank-parser"})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    print(f"[Parser] Starting on :{port}", flush=True)
    app.run(host='0.0.0.0', port=port, debug=False)
