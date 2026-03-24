# FinParse — Bank Statement Analyser
**Stack:** Angular 17 · Spring Boot 3 · PostgreSQL · Python/Flask**

---

## Architecture

```
Browser (Angular :4200)
       │  HTTP
       ▼
Spring Boot (:8080)   ← REST API, stores data in PostgreSQL
       │  HTTP (multipart PDF)
       ▼
Python/Flask (:5050)  ← pdfplumber, camelot, PyMuPDF parser
       │
       ▼
PostgreSQL (:5432)    ← statements + transactions tables
```

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

### 1 — Find your IP

```bash
ip a | grep "inet " | grep -v 127
# look for something like 192.168.x.x or 10.x.x.x
```

### 2 — Set up PostgreSQL

```bash
sudo systemctl start postgresql
sudo -u postgres psql -f setup_db.sql
# Creates user 'bankparser' with password 'bankparser123'
# Creates database 'bankparser'
```

### 3 — Python virtual environment

```bash
cd python-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

### 4 — Patch your IP into configs

Edit **two** files, replacing `YOUR_IP` with your actual IP:

**`frontend/src/environments/environment.ts`**
```typescript
export const environment = {
  production: false,
  apiUrl: 'http://192.168.1.100:8080'   // ← your IP
};
```

**`backend/src/main/resources/application.properties`**
```properties
cors.allowed.origins=http://192.168.1.100:4200,http://localhost:4200
```

### 5 — Build backend

```bash
cd backend
mvn clean package -DskipTests
# Creates: target/bank-parser-backend-1.0.0.jar
```

### 6 — Install Angular dependencies

```bash
cd frontend
npm install
```

---

## Running (every time)

### Option A — One command (recommended)

```bash
bash start.sh                    # auto-detects IP
# OR
bash start.sh 192.168.1.100      # explicit IP
```

This starts all three services in the background.

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
# Open http://YOUR_IP:4200
```

---

## Stopping

```bash
bash stop.sh
```

---

## Using the App

1. Open `http://YOUR_IP:4200` in any browser on the same network
2. Click **New Statement**
3. Fill in analyst details (name, bank, period etc.)
4. Drag & drop or browse for a bank statement PDF
5. Click **Parse Statement**
6. If the PDF is password-protected, a prompt appears for the password
7. After parsing, click **View Transactions** to see the data
8. Click **↓ Download CSV** to export

---

## Service Ports

| Service | Port | URL |
|---------|------|-----|
| Angular UI | 4200 | `http://YOUR_IP:4200` |
| Spring Boot API | 8080 | `http://YOUR_IP:8080/api/statements` |
| Python Parser | 5050 | `http://localhost:5050/health` |
| PostgreSQL | 5432 | localhost only |

---

## Supported Banks

AU Small Finance Bank · HDFC · SBI · ICICI · Axis · Kotak · PNB ·
Bank of Baroda · Canara · Union Bank · IDFC First · Yes Bank ·
IndusInd · Federal · IOB

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
