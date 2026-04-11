# Contributing to FinParse — Bank Statement Analyser

Thank you for considering a contribution! This document explains the project layout and the steps to get a change merged.

---

## Repository layout

```
bank-statement-analyzer/
├── python-service/         ← Flask microservice (parsing engine)
│   ├── app.py              ← REST API routes
│   ├── requirements.txt
│   └── bank_parser/
│       ├── pipeline.py     ← Orchestrates extraction → mapping → validation → insights
│       ├── extractor/      ← PDF (pdfplumber / camelot) and spreadsheet engines
│       ├── processors/     ← Header detection, row reconstruction
│       ├── semantic/       ← Column mapping, bank detection, transaction categorisation
│       ├── validators/     ← Balance-continuity validation
│       └── analytics/      ← EMI detection, financial insights, underwriting scorecard
├── backend/                ← Spring Boot 3 REST API (stores data in PostgreSQL)
│   └── src/main/java/com/bankparser/
├── frontend/               ← Angular 17 single-page application
│   └── src/app/
├── setup_db.sql
├── setup.sh
├── start.sh
└── stop.sh
```

---

## Development workflow

### 1. Fork & branch

```bash
# Fork the repo on GitHub, then:
git clone https://github.com/<your-username>/bank-statement-analyzer.git
cd bank-statement-analyzer
git checkout -b feature/<short-description>
```

### 2. Set up the environment

Follow the **First-Time Setup** steps in [README.md](README.md) to install all prerequisites and configure PostgreSQL.

### 3. Make your changes

| Area | What to touch |
|------|---------------|
| Add / fix a bank parser | `python-service/bank_parser/semantic/bank_detector.py` (signatures & overrides) |
| Fix extraction for a specific bank | `python-service/bank_parser/extractor/` |
| Add a new transaction category | `python-service/bank_parser/semantic/categorizer.py` |
| Add a new analytics metric | `python-service/bank_parser/analytics/insights.py` |
| Add a Spring Boot endpoint | `backend/src/main/java/com/bankparser/controller/` |
| Change UI behaviour | `frontend/src/app/components/` |

### 4. Run the services locally

```bash
bash start.sh          # starts Python :5050, Spring Boot :8080, Angular :4200
bash stop.sh           # stops all services
```

Smoke-test the parser:

```bash
curl http://localhost:5050/health
curl http://localhost:5050/supported-banks
```

### 5. Python code style

- Follow **PEP 8**.
- Keep new functions/classes small and focused.
- Add a one-line docstring to every public function.

### 6. Commit messages

Use the conventional-commit format:

```
<type>(<scope>): <short summary>

feat(parser): add UCO Bank signature detection
fix(insights): handle empty DataFrame in EMI detector
docs: update CONTRIBUTING.md
```

Types: `feat` | `fix` | `refactor` | `docs` | `test` | `chore`

### 7. Open a pull request

- Target the **main** branch.
- Describe *what* changed and *why*.
- Reference any related issue: `Closes #42`.

---

## Adding support for a new bank

1. Open `python-service/bank_parser/semantic/bank_detector.py`.
2. Add an entry to `BANK_SIGNATURES` with the bank's letterhead keywords (lowercase).
3. Optionally add structural hints to `BANK_OVERRIDES` (date format, empty-cell markers, etc.).
4. Test with a real statement PDF from that bank.

---

## Reporting bugs

Open a GitHub Issue and include:

- Bank name and file format (PDF / XLSX / CSV)
- The error message or screenshot
- Whether the PDF is password-protected

---

## Questions?

Open a Discussion or ping the maintainers in the issue tracker.
