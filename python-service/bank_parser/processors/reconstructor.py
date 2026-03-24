import re
import pandas as pd
from typing import Optional
from semantic.column_mapper import clean_balance_cr_dr

DATE_FORMATS = [

]

DATE_WORD_RE = re.compile(
    r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}\b',
    re.IGNORECASE
)
DATE_NUM_RE = re.compile(r'\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b')


def _is_empty(val) -> bool:
    return pd.isna(val) or str(val).strip().lower() in ('', 'nan', 'none', '-', '--', 'nat')


