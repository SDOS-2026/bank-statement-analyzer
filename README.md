# FinParse — Bank Statement Analyser
**Stack:** Angular 17 · Spring Boot 3 · PostgreSQL · Python/Flask

---

## Architecture

```
Browser / Vercel-hosted Angular
       │  JWT-authenticated HTTPS
       ▼
Spring Boot API (:8080)   ← auth, statement ownership, internal/user separation
       │  HTTP (multipart file parse)
       ▼
Python/Flask (:5050)      ← parser + insights + scorecard generation
       │
       ▼
PostgreSQL (:5432)        ← users, statements, transactions
```

Two dashboard modes now exist:

- `USER`: can register/login, upload multiple statements, and only access their own statements and analysis
- `INTERNAL`: can review all uploaded statements across users from a separate internal dashboard

The backend enforces ownership checks on statement list/detail/transactions/insights/scorecard/export/delete routes.

---

## Prerequisites (install once)

```bash
# Ubuntu / Debian
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv \
  openjdk-21-jdk maven nodejs npm \
  postgresql postgresql-contrib ghostscript
sudo npm install -g @angular/cli@17
```

---

## First-Time Setup

### 1 — Set up PostgreSQL

```bash
sudo systemctl start postgresql
sudo -u postgres psql -f setup_db.sql
# Creates local dev DB/user
```

### 2 — Python virtual environment

```bash
cd python-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

### 3 — Build backend

```bash
cd backend
mvn clean package -DskipTests
# Creates: target/bank-parser-backend-1.0.0.jar
```

### 4 — Install Angular dependencies

```bash
cd frontend
npm install
```

### 5 — Configure local environment

Frontend:

```bash
cd frontend
cp .env.example .env.local
# set NG_APP_API_URL=http://localhost:8080
```

Backend important env vars:

```bash
SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/bankparser
SPRING_DATASOURCE_USERNAME=bankparser
SPRING_DATASOURCE_PASSWORD=bankparser123
PARSER_SERVICE_URL=http://localhost:5050
CORS_ALLOWED_ORIGINS=http://localhost:4200
APP_JWT_SECRET=replace-with-a-long-random-secret
APP_BOOTSTRAP_INTERNAL_EMAIL=internal@example.com
APP_BOOTSTRAP_INTERNAL_PASSWORD=replace-with-a-strong-password
APP_BOOTSTRAP_INTERNAL_NAME=FinParse Internal Admin
```

---

## Running (every time)

### Option A — One command (recommended)

```bash
bash start.sh                    # auto-detects IP
# OR
bash start.sh 192.168.1.100      # explicit IP
```

This starts all three services in the background for local development.

### Option B — Three terminals manually

**Terminal 1 — Python parser:**
```bash
cd python-service
source venv/bin/activate
python app.py
# Running on http://0.0.0.0:5050
```

**Terminal 2 — Spring Boot:**
```bash
cd backend
java -jar target/bank-parser-backend-1.0.0.jar
# Started on port 8080
```

**Terminal 3 — Angular:**
```bash
cd frontend
ng serve --host 0.0.0.0 --port 4200
# Open http://localhost:4200
```

---

## Stopping

```bash
bash stop.sh
```

---

## Using the App

1. Open `http://localhost:4200`
2. Create a user account or sign in
3. Upload one or more statements from the user dashboard
4. If a file is password-protected, enter the password after upload
5. Review the parsed transactions, insights, and underwriting scorecard
6. Sign in with the bootstrapped internal account to access the internal dashboard

---

## Service Ports

| Service | Port | URL |
|---------|------|-----|
| Angular UI | 4200 | `http://localhost:4200` |
| Spring Boot API | 8080 | `http://localhost:8080/api/statements` |
| Python Parser | 5050 | `http://localhost:5050/health` |
| PostgreSQL | 5432 | localhost only |

---

## Supported Banks

AU Small Finance Bank · HDFC · SBI · ICICI · Axis · Kotak · PNB ·
Bank of Baroda · Canara · Union Bank · IDFC First · Yes Bank ·
IndusInd · Federal · IOB · Indian Bank / Allahabad Bank · UCO ·
Central Bank · Punjab & Sind Bank · Paytm statement exports

---

## Underwriting & Domain Rules

FinParse includes a deterministic underwriting policy engine in
`python-service/bank_parser/analytics/underwriting.py`. It returns:

- statement-based score and risk band
- eligibility decision (`APPROVE`, `CONDITIONAL`, `MANUAL_REVIEW`, `DECLINE`)
- product recommendations with indicative maximum amount and EMI
- adverse-action-style principal reasons
- policy assumptions and version

Read the internal architecture and policy document:
`docs/UNDERWRITING_ARCHITECTURE.md`

Run Python tests:

```bash
cd python-service
venv/bin/python -m unittest discover -s tests
```

---

## Deployment

Production deployment is split by responsibility:

- Frontend: deploy `frontend/` to Vercel
- Backend API: deploy `backend/` on a JVM-friendly host
- Parser service: deploy `python-service/` on a Python host with `ghostscript` available
- Database: managed PostgreSQL

Read the deployment runbook:
`docs/DEPLOYMENT.md`

---

## Checking logs

```bash
tail -f /tmp/finparse-python.log    # parser output
tail -f /tmp/finparse-backend.log   # spring boot
tail -f /tmp/finparse-angular.log   # angular dev server
```

---

## Database direct access

```bash
psql -U bankparser -d bankparser -h localhost
# password: bankparser123

\dt                                  -- list tables
SELECT * FROM statements;
SELECT * FROM transactions WHERE statement_id = 1 LIMIT 10;
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Connection refused :8080` | Spring Boot still starting (~20s). Check log. |
| `Connection refused :5050` | Python venv not activated or flask not installed |
| `CORS error in browser` | Check `cors.allowed.origins` in application.properties matches your IP |
| `No transactions extracted` | PDF might be image-based (scanned). Try another file. |
| `407 Proxy Error (Maven)` | Set `MAVEN_OPTS` or use a settings.xml with no proxy |
| Angular shows blank page | Open browser console — likely API URL mismatch in environment.ts |
| PostgreSQL auth failed | Run `sudo -u postgres psql -f setup_db.sql` again |

---

## File Structure

```
bankapp/
├── python-service/         ← Flask + parser engine
│   ├── app.py              ← REST API wrapping the parser
│   ├── requirements.txt
│   └── bank_parser/        ← All the extraction logic
│       ├── pipeline.py
│       ├── extractor/
│       ├── processors/
│       ├── semantic/
│       └── validators/
├── backend/                ← Spring Boot
│   ├── pom.xml
│   └── src/main/java/com/bankparser/
│       ├── BankParserApplication.java
│       ├── controller/StatementController.java
│       ├── service/StatementService.java
│       ├── model/{Statement,Transaction}.java
│       ├── repository/
│       └── config/
├── frontend/               ← Angular 17
│   └── src/app/
│       ├── components/
│       │   ├── dashboard/
│       │   ├── upload/
│       │   └── statement-detail/
│       ├── services/statement.service.ts
│       └── models/statement.model.ts
├── setup_db.sql
├── setup.sh                ← Full first-time setup
├── start.sh                ← Start all services
├── stop.sh                 ← Stop all services
└── README.md
```
