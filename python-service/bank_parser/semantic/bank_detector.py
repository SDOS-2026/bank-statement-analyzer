import fitz
import re

# Signatures must only match the *bank's own name*, not customer UPI refs.
# We check the first ~300 characters of page 1 which is the letterhead.
BANK_SIGNATURES = {
    "AU_SMALL_FINANCE":  ["au small finance bank", "aubank", "au bank"],
    "HDFC":              ["hdfc bank"],
    "SBI":               ["state bank of india"],
    "ICICI":             ["icici bank"],
    "AXIS":              ["axis bank"],
    "PNB":               ["punjab national bank"],
    "KOTAK":             ["kotak mahindra bank", "kotak bank"],
    "BOB":               ["bank of baroda"],
    "CANARA":            ["canara bank"],
    "IDFC":              ["idfc first bank"],
    "YES":               ["yes bank"],
    "INDUSIND":          ["indusind bank"],
    "FEDERAL":           ["federal bank"],
    "IOB":               ["indian overseas bank"],
    "CENTRAL_BANK":      ["central bank of india"],
    "UCO":               ["uco bank"],
    "UNION":             ["union bank", "union bank of india"],
    "INDIAN_BANK":       ["indian bank"],
    "PAYTM":             ["paytm payments bank", "paytm statement"],
}

# Per-bank structural hints used by the column mapper / reconstructor
BANK_OVERRIDES = {
    "AU_SMALL_FINANCE": {
        "empty_marker": "-",          # AU uses '-' for blank Debit/Credit
        "date_format": "%d %b %Y",    # '01 Feb 2026'
    },
    "HDFC": {
        "empty_marker": "",
        "date_format": "%d/%m/%Y",
    },
    "SBI": {
        "empty_marker": "",
        "grouped_dates": True,
        "date_format": "%d %b %Y",
    },
    "ICICI": {
        "empty_marker": "",
        "date_format": "%d/%m/%Y",
    },
    "AXIS": {
        "empty_marker": "",
        "combined_amount": True,
    },
    "UNION": {
        "combined_amount": True,
    },
    "CENTRAL_BANK": {
        "grouped_dates": True,
    },
    "UCO": {
        "grouped_dates": True,
    },
}

MANUAL_BANK_HINTS = {
    "au small finance bank": "AU_SMALL_FINANCE",
    "au bank": "AU_SMALL_FINANCE",
    "hdfc bank": "HDFC",
    "hdfc": "HDFC",
    "state bank of india": "SBI",
    "sbi": "SBI",
    "icici bank": "ICICI",
    "icici": "ICICI",
    "axis bank": "AXIS",
    "axis": "AXIS",
    "punjab national bank": "PNB",
    "pnb": "PNB",
    "kotak mahindra bank": "KOTAK",
    "kotak bank": "KOTAK",
    "kotak": "KOTAK",
    "bank of baroda": "BOB",
    "bob": "BOB",
    "canara bank": "CANARA",
    "canara": "CANARA",
    "union bank of india": "UNION",
    "union bank": "UNION",
    "union": "UNION",
    "idfc first bank": "IDFC",
    "idfc": "IDFC",
    "yes bank": "YES",
    "yes": "YES",
    "indusind bank": "INDUSIND",
    "indusind": "INDUSIND",
    "federal bank": "FEDERAL",
    "federal": "FEDERAL",
    "indian overseas bank": "IOB",
    "iob": "IOB",
    "bank of allahabad": "INDIAN_BANK",
    "allahabad bank": "INDIAN_BANK",
    "indian bank": "INDIAN_BANK",
}


def normalize_bank_name(bank_name: str | None) -> str:
    if not bank_name:
        return "UNKNOWN"

    cleaned = re.sub(r'[^a-z0-9]+', ' ', bank_name.lower()).strip()
    if not cleaned or cleaned == "other":
        return "UNKNOWN"

    internal_code = cleaned.upper().replace(' ', '_')
    if internal_code in BANK_SIGNATURES:
        return internal_code

    for hint, bank in MANUAL_BANK_HINTS.items():
        if cleaned == hint or cleaned.startswith(hint) or hint.startswith(cleaned):
            return bank

    return "UNKNOWN"


def detect_bank(pdf_path: str, password: str = None) -> str:
    """
    Read ONLY the first page of the PDF and look for the bank's letterhead.
    Crucially, we restrict to the top portion of the page to avoid matching
    bank names that appear in UPI transaction narrations.
    """
    try:
        doc = fitz.open(pdf_path)
        if doc.is_encrypted:
            if not password or doc.authenticate(password) == 0:
                return "UNKNOWN"
        page = doc[0]

        # Get structured blocks sorted top-to-bottom
        blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, ...)
        # Take only top 30% of page height for letterhead
        page_height = page.rect.height
        top_cutoff = page_height * 0.30

        header_text = ""
        for block in blocks:
            if block[1] < top_cutoff:   # y0 < cutoff
                header_text += block[4].lower() + " "

        # Also check the full first page for bank name in a structured field
        full_first_page = page.get_text().lower()

        for bank, signatures in BANK_SIGNATURES.items():
            for sig in signatures:
                if sig in header_text:
                    return bank

        # Fallback: check full page but require the signature to appear
        # near common label patterns like "bank name:", "issuing bank:", etc.
        for bank, signatures in BANK_SIGNATURES.items():
            for sig in signatures:
                if sig in full_first_page:
                    # Make sure it's not just in a UPI narration
                    # UPI narrations typically follow patterns like SBIN/, ICIC/
                    # We check: does the sig appear outside of a UPI string?
                    pattern = rf'(?<!upi)(?<!neft)(?<!imps)\b{re.escape(sig)}\b'
                    if re.search(pattern, full_first_page):
                        return bank

        return "UNKNOWN"
    except Exception:
        return "UNKNOWN"


def get_bank_overrides(bank: str) -> dict:
    return BANK_OVERRIDES.get(bank, {})
