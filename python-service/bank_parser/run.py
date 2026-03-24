"""
Entry point: python run.py <path_to_pdf>
"""

import sys
import os

# Make sure imports work regardless of where run.py is called from
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from pipeline import parse_bank_statement


def main():
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "bank.pdf"

    print(f"\n{'='*55}")
    print(f"  Processing: {pdf_path}")
    print(f"{'='*55}\n")

    result = parse_bank_statement(pdf_path)

    df     = result["dataframe"]
    report = result["validation"]

    print(f"\n{'='*55}")
    print(f"  RESULT SUMMARY")
    print(f"{'='*55}")
    print(f"  Bank Detected   : {result['bank']}")
    print(f"  Engine Used     : {result['engine_used']}")
    print(f"  Total Rows      : {report.total_rows}")
    print(f"  Confidence      : {report.confidence_score:.1%}")
    print(f"  Balance Errors  : {len(report.balance_mismatches)}")
    print(f"  Status          : {'✅ PASSED' if result['success'] else '⚠  LOW CONFIDENCE'}")
    print(f"{'='*55}\n")

    if not df.empty:
        pd.set_option('display.max_colwidth', 60)
        pd.set_option('display.width', 200)
        print("--- Transactions (first 10) ---")
        print(df.head(10).to_string(index=True))

        print(f"\n--- Debit total : ₹{df['Debit'].sum():,.2f}")
        print(f"--- Credit total: ₹{df['Credit'].sum():,.2f}")

        out_path = pdf_path.replace(".pdf", "_extracted.csv")
        df.to_csv(out_path, index=False)
        print(f"\n✅ Saved to: {out_path}")

        if report.balance_mismatches:
            flagged = df.copy()
            flagged['_balance_error'] = flagged.index.isin(report.balance_mismatches)
            flag_path = pdf_path.replace(".pdf", "_flagged.csv")
            flagged.to_csv(flag_path, index=False)
            print(f"⚠  Flagged rows: {flag_path}")

        if report.suspicious_rows:
            print(f"\n⚠  Suspicious rows (both Debit & Credit filled):")
            print(df.iloc[report.suspicious_rows].to_string())
    else:
        print("❌ No transactions extracted.")


if __name__ == "__main__":
    main()
