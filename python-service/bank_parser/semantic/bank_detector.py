
import fitz
import re

# Signatures must only match the *bank's own name*, not customer UPI refs.
# We check the first ~300 characters of page 1 which is the letterhead.
BANK_SIGNATURES = {
    
}

# Per-bank structural hints used by the column mapper / reconstructor
BANK_OVERRIDES = {

}


