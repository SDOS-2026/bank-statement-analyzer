import re
import pandas as pd
from typing import Tuple

DATE_PATTERN = re.compile(
    r'\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b'       # 01/02/2024
    r'|\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b',  # 01 Feb 2026
    re.IGNORECASE
)
AMOUNT_PATTERN = re.compile(r'\b\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?\b')

HEADER_KEYWORDS = {

}


def _flatten(val: str) -> str:
    """Replace newlines and extra spaces inside a cell value."""
    return re.sub(r'\s+', ' ', str(val).replace('\n', ' ')).strip().lower()





