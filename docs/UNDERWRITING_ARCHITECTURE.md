# FinParse Underwriting Architecture

Status: internal engineering and product policy reference
Policy version in code: `statement-underwriting-v1.0`

## Purpose

FinParse parses bank statements and turns the extracted cashflow into an auditable lending recommendation. The system must not behave like a vague "loan score" black box. Every output should answer:

- Is the applicant eligible, conditionally eligible, manual-review, or declined?
- What loan products are realistic?
- What is the indicative maximum amount and EMI capacity?
- Which facts drove the recommendation?
- Which checks are still outside bank-statement analytics?

The current engine is rule-based and deterministic. It is suitable as a deployable decision-support layer, not as a final regulated credit decision without lender policy approval, KYC, bureau data, employment checks, fraud checks, and legal/compliance review.

## Regulatory Guardrails

This code is shaped around explainability and borrower protection, not only prediction.

- RBI Digital Lending Directions, 2025 require regulated entities to assess borrower creditworthiness from the borrower economic profile before extending digital loans, keep the information for audit, provide disclosures, maintain grievance redressal, and handle borrower data with explicit consent and storage controls: https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12848&Mode=0
- RBI Key Facts Statement rules require KFS/APR disclosure for retail and MSME term loans, and define APR as annual cost including interest and other charges: https://rbi.org.in/Scripts/BS_CircularIndexDisplay.aspx?Id=12663
- CFPB Regulation B requires adverse-action reasons to be specific and tied to factors actually considered or scored; generic "failed internal score" reasons are not enough: https://www.consumerfinance.gov/rules-policy/regulations/1002/9/
- CFPB guidance on algorithmic credit decisions says creditors must be able to provide specific and accurate reasons even when using complex models: https://www.consumerfinance.gov/compliance/circulars/circular-2022-03-adverse-action-notification-requirements-in-connection-with-credit-decisions-based-on-complex-algorithms/
- CFPB explains DTI as monthly debt payments divided by gross monthly income and notes that lenders use it to assess repayment capacity, with limits varying by product and lender: https://www.consumerfinance.gov/ask-cfpb/what-is-a-debt-to-income-ratio-en-1791/

Because this app works mainly on Indian bank statements, the code uses INR terminology and FOIR-style affordability. The same architecture can be localized for other jurisdictions by replacing policy values, disclosure language, and compliance workflows.

## System Architecture

```
Angular UI
  Upload statement, show parser confidence, insights, scorecard, products

Spring Boot API
  Stores statement metadata, transactions, insights JSON, scorecard JSON
  Exposes /api/statements/{id}/insights and /scorecard

Python parser service
  /parse accepts PDF/XLS/XLSX/ODS/CSV
  Detects bank, extracts transactions, validates balance arithmetic
  Categorizes transactions and computes insights
  Runs underwriting policy engine

PostgreSQL
  statements table stores parser metadata and JSON analytics
  transactions table stores normalized statement rows
```

## Parser Pipeline

File: `python-service/bank_parser/pipeline.py`

1. File type routing
   - Spreadsheets use `extract_spreadsheet`.
   - PDFs use multi-engine extraction.
   - Password-protected PDFs now return `status=password_required` from the pipeline itself.

2. Bank detection
   - File: `semantic/bank_detector.py`
   - Uses header text, full first-page fallback, IFSC prefixes, and filename fallback when text is encrypted or non-branded.
   - Bank detection is intentionally scoped to issuer signals so UPI narration bank names do not override the statement issuer.

3. Extraction engines
   - File: `extractor/engine_runner.py`
   - Tries `pdfplumber`, Camelot lattice/stream, PyMuPDF, and text-row reconstruction.
   - Text-row fallback now handles serial-number-prefixed rows such as ICICI where `1 02.11.2025` should parse as date `02.11.2025`, not day `1`.

4. Header and column mapping
   - Files: `processors/header_detector.py`, `semantic/column_mapper.py`
   - Maps bank-specific headers to canonical columns: `Date`, `Description`, `Debit`, `Credit`, `Balance`, `Reference`.

5. Reconstruction and validation
   - File: `processors/reconstructor.py`
   - Cleans dates, descriptions, amount formats, CR/DR balance suffixes, and multiline descriptions.
   - File: `validators/transaction_validator.py`
   - Performs balance continuity checks and treats NaN debit/credit as zero so validation does not silently skip bad rows.

6. Categorization and insights
   - Files: `semantic/categorizer.py`, `analytics/insights.py`
   - Categorizes salary, business income, EMI, transfers, fees, food, utilities, rent, insurance, etc.
   - Computes monthly income, expenses, savings, EMI burden, balance signals, detected recurring EMIs, category totals, and income stability.

7. Underwriting
   - File: `analytics/underwriting.py`
   - Produces score, decision, product recommendations, max amount, EMI, adverse-action-style reasons, and policy assumptions.

## Underwriting Inputs

The policy engine consumes `FinancialInsights`, not raw statement rows. Key inputs:

- `months_analyzed`
- `income_months`
- `avg_monthly_income`
- `avg_monthly_expenses`
- `avg_balance`
- `savings_rate`
- `emi_burden_ratio`
- `income_stability_score`
- `bounce_count`
- `negative_balance_months`
- `detected_emis`

Important limitation: bank statements show observed inflow, not verified gross income. The engine treats income as net observed cashflow and makes this assumption visible in the scorecard.

## Scorecard

The score remains 0-100 but each component is explicit:

| Component | Max | What it measures |
| --- | ---: | --- |
| Income Stability | 25 | Recurring income regularity and number of income months |
| Existing Debt Burden | 20 | Existing EMI burden as percentage of observed income |
| Cashflow Surplus | 20 | Savings rate and whether spending exceeds income |
| Liquidity Buffer | 15 | Average balance relative to monthly income |
| Account Conduct | 10 | Low-balance and negative-balance months |
| Income Level | 10 | Observed monthly income tier |

Risk bands:

| Score | Band |
| ---: | --- |
| 80-100 | EXCELLENT |
| 65-79 | GOOD |
| 50-64 | FAIR |
| 35-49 | POOR |
| 0-34 | VERY_POOR |

Decision mapping:

| Decision | Meaning |
| --- | --- |
| APPROVE | At least one product is eligible under policy |
| CONDITIONAL | Product may be offered only with mitigants or stricter verification |
| MANUAL_REVIEW | Score is not a straight decline, but no product passes automated rules |
| DECLINE | Statement-based profile fails policy |

## Affordability Formula

The engine computes new EMI capacity conservatively:

```
existing_emi = avg_monthly_income * emi_burden_ratio / 100
foir_capacity = avg_monthly_income * product_max_foir_pct / 100 - existing_emi
surplus_capacity = (avg_monthly_income - avg_monthly_expenses) * residual_buffer_pct / 100
new_emi_capacity = max(0, min(foir_capacity, surplus_capacity))
```

The loan principal supported by that EMI is:

```
monthly_rate = annual_rate_pct / 1200
principal = EMI * (1 - (1 + monthly_rate) ^ -tenure_months) / monthly_rate
```

Final amount is the minimum of:

- amount supported by EMI,
- product income-multiple cap,
- product absolute cap.

Then it is rounded down to the nearest INR 1,000.

## Current Product Policies

These are conservative starter policies. A lender should tune them to its approved credit policy and product economics before production launch.

| Product | Secured | Min approve score | Review score | Min income | History | Max FOIR | Indicative APR | Tenure | Caps |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Unsecured personal loan | No | 70 | 58 | 25,000 | 3 mo | 40% | 16% | 60 mo | 18x income, 20 lakh |
| Two-wheeler loan | Yes | 58 | 48 | 12,000 | 3 mo | 45% | 13% | 48 mo | 10x income, 3 lakh |
| Vehicle loan | Yes | 64 | 52 | 30,000 | 3 mo | 50% | 11% | 84 mo | 30x income, 50 lakh |
| Home loan | Yes | 72 | 60 | 40,000 | 6 mo | 50% | 9% | 240 mo | 60x income, 2 crore |
| MSME working-capital term loan | Yes | 68 | 56 | 50,000 | 6 mo | 45% | 18% | 36 mo | 6x income, 30 lakh |

Product output includes:

- `status`: `ELIGIBLE`, `CONDITIONAL`, or `NOT_ELIGIBLE`
- `max_amount`
- `monthly_emi`
- `tenure_months`
- `indicative_apr`
- `reasons`
- `mitigants`

## Adverse-Action-Style Reasons

The scorecard returns `adverse_action_reasons`, capped to the first four principal reasons. These are generated only from factors actually used in the rule engine, for example:

- Insufficient statement history
- Insufficient recurring income evidence
- Unstable or irregular income pattern
- Existing EMI burden is too high
- Negative monthly cashflow
- Negative account balance observed
- Low-balance account conduct observed
- Overall statement-based score below policy threshold

These are not a complete legal adverse-action notice. They are the engineering primitive a compliance-approved notice generator can use.

## Tests

Run core tests:

```bash
cd python-service
venv/bin/python -m unittest discover -s tests
```

Current tests cover:

- compact bank-name normalization,
- sample PDF bank-detection priority for Axis, Paytm, PNB, and UCO,
- encrypted PDF password-required behavior,
- ICICI-style text rows with serial number before date,
- balance validation with NaN amounts,
- high-quality cashflow approval,
- high EMI burden,
- insufficient history,
- negative cashflow,
- present-value loan calculation.

## Production Checklist

Before real lending use:

- Add bureau-score and credit-report inputs.
- Add identity/KYC, fraud, sanctions, and duplicate-applicant checks.
- Add employment/business verification status.
- Add collateral valuation for secured products.
- Add jurisdiction-specific adverse-action and borrower disclosure templates.
- Add lender-approved APR, fee, tenure, and product configuration from database or admin console.
- Add audit logs that persist input facts, policy version, output, reasons, and analyst overrides.
- Add model-risk/compliance sign-off for any future statistical or ML model.
- Add data-retention, consent, deletion, and encryption controls aligned with the deployment jurisdiction.

## Known Limitations

- Statement parsing still depends on PDF quality; scanned/image-only PDFs need OCR.
- Income categorization from narrations can misclassify transfers as income unless bank-specific salary/business rules are improved.
- Current affordability does not include bureau debt not visible in statements.
- Product APRs are indicative constants, not live pricing.
- Business underwriting is simplified and does not yet analyze GST, invoices, seasonality, inventory, or receivables.
