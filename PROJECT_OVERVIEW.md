# Bank Statement Analyzer - Comprehensive Project Overview

## Executive Summary
A full-stack web application for parsing and analyzing bank statements in multiple formats (PDF, XLSX, XLS, ODS, CSV). Architecture includes Java/Spring backend, Angular frontend, and Python microservice for parsing.

---

## 1. BACKEND (Java/Spring)

### Stack & Frameworks
- **Framework**: Spring Boot 3.2.5
- **Java Version**: 21
- **Database**: PostgreSQL
- **Build Tool**: Maven
- **Test Framework**: JUnit 5, Mockito
- **Key Dependencies**:
  - Spring Web, Spring Security, Spring Data JPA
  - Jackson (JSON processing)
  - Apache Commons CSV
  - PostgreSQL Driver

### REST API Endpoints

#### HealthController
- **File**: [backend/src/main/java/com/bankparser/controller/HealthController.java](backend/src/main/java/com/bankparser/controller/HealthController.java)
- **Endpoints**:
  - `GET /api/health` - Health check

#### AuthController
- **File**: [backend/src/main/java/com/bankparser/controller/AuthController.java](backend/src/main/java/com/bankparser/controller/AuthController.java)
- **Endpoints**:
  - `POST /api/auth/register` - User registration
  - `POST /api/auth/login` - User login with JWT
  - `POST /api/auth/forgot-password` - Password reset
  - `GET /api/auth/me` - Get current user

#### StatementController
- **File**: [backend/src/main/java/com/bankparser/controller/StatementController.java](backend/src/main/java/com/bankparser/controller/StatementController.java)
- **Endpoints**:
  - `GET /api/statements` - List statements (mine/all scope)
  - `POST /api/statements` - Upload and parse file (multipart/form-data)
  - `GET /api/statements/{id}` - Get statement by ID
  - `POST /api/statements/{id}/unlock` - Unlock password-protected statement
  - `GET /api/statements/{id}/transactions` - Get transactions for statement
  - `GET /api/statements/{id}/insights` - Get financial insights JSON
  - `GET /api/statements/{id}/scorecard` - Get underwriting scorecard
  - `GET /api/statements/{id}/export/csv` - Export transactions as CSV
  - `DELETE /api/statements/{id}` - Delete statement

### Services

#### StatementService
- **File**: [backend/src/main/java/com/bankparser/service/StatementService.java](backend/src/main/java/com/bankparser/service/StatementService.java)
- **Key Methods**:
  - `uploadAndParse(MultipartFile, StatementUploadRequest)` - Upload file and call parser microservice
  - `unlockWithPassword(Long, String)` - Retry parsing with password for encrypted files
  - `getStatements(String scope)` - Retrieve user's statements (mine/all)
  - `getStatement(Long id)` - Get single statement by ID
  - `getTransactions(Long statementId)` - Fetch transactions for a statement
  - `getInsights(Long statementId)` - Parse and return insights JSON
  - `getScorecard(Long statementId)` - Parse and return scorecard JSON
  - `deleteStatement(Long id)` - Delete statement and related transactions
  - `callParser(MultipartFile, String, String, String)` - HTTP call to Python parser service
  - `applyParserResult(Statement, Map)` - Process parser response and update statement

#### AppUserService
- **File**: [backend/src/main/java/com/bankparser/service/AppUserService.java](backend/src/main/java/com/bankparser/service/AppUserService.java)
- **Key Methods**:
  - `registerUser(RegisterRequest)` - Create new user account
  - `resetPassword(String, String, String)` - Reset user password with validation
  - `getCurrentUser()` - Get authenticated user from SecurityContext
  - `bootstrapInternalUser(String, String, String)` - Create/update internal admin user
  - `loadUserByUsername(String)` - Spring UserDetailsService implementation

#### BootstrapService
- **File**: [backend/src/main/java/com/bankparser/service/BootstrapService.java](backend/src/main/java/com/bankparser/service/BootstrapService.java)
- **Purpose**: Initialize database with default internal user

### Test Structure

#### StatementControllerTest
- **File**: [backend/src/test/java/com/bankparser/controller/StatementControllerTest.java](backend/src/test/java/com/bankparser/controller/StatementControllerTest.java)
- **Test Pattern**: Uses `@ExtendWith(MockitoExtension.class)` + Mockito mocks
- **Tests Covered**:
  - `listDefaultsToMineScope()` - List statements with default scope
- **Framework**: JUnit 5, Mockito, AssertJ assertions

#### StatementServiceTest
- **File**: [backend/src/test/java/com/bankparser/service/StatementServiceTest.java](backend/src/test/java/com/bankparser/service/StatementServiceTest.java)
- **Test Pattern**: Unit tests with mocked repositories and RestTemplate
- **Mocks Used**: 
  - StatementRepository
  - TransactionRepository
  - RestTemplate
  - AppUserService

### Data Models
- **Statement** - Bank statement metadata (customer name, bank, account, status, etc.)
- **Transaction** - Individual transaction row (date, description, debit, credit, balance, reference)
- **AppUser** - User account (email, password hash, role, active status)
- **UserRole** - ENUM (USER, INTERNAL)

---

## 2. FRONTEND (Angular)

### Stack & Frameworks
- **Framework**: Angular 17.3
- **Language**: TypeScript 5.4
- **Build Tool**: Angular CLI
- **Test Framework**: Jasmine 5.1 + Karma 6.4
- **UI Framework**: Angular Material 17.3
- **State Management**: Angular signals
- **HTTP Client**: Angular HttpClient

### Services

#### AuthService
- **File**: [frontend/src/app/services/auth.service.ts](frontend/src/app/services/auth.service.ts)
- **HTTP Methods**:
  - `login(payload)` - POST `/api/auth/login`
  - `register(payload)` - POST `/api/auth/register`
  - `forgotPassword(payload)` - POST `/api/auth/forgot-password`
  - `restoreSession()` - GET `/api/auth/me` (restore from token)
- **Local State**:
  - `user` - Signal with current authenticated user
  - `getToken()` - Retrieve JWT from localStorage
  - `isAuthenticated()` - Check if token exists
  - `isInternal()` - Check if user role is INTERNAL
  - `persistSession(response)` - Store token and user
  - `logout()` - Clear token and user state

#### StatementService
- **File**: [frontend/src/app/services/statement.service.ts](frontend/src/app/services/statement.service.ts)
- **HTTP Methods**:
  - `getAll(scope)` - GET `/api/statements?scope=mine|all`
  - `getById(id)` - GET `/api/statements/{id}`
  - `upload(file, meta)` - POST `/api/statements` (multipart/form-data)
  - `unlock(id, password)` - POST `/api/statements/{id}/unlock`
  - `getTransactions(id)` - GET `/api/statements/{id}/transactions`
  - `getInsights(id)` - GET `/api/statements/{id}/insights`
  - `getScorecard(id)` - GET `/api/statements/{id}/scorecard`
  - `downloadCsv(id)` - GET `/api/statements/{id}/export/csv` (blob response)
  - `delete(id)` - DELETE `/api/statements/{id}`

### Components with Specs

#### UploadComponent
- **Files**: 
  - Component: [frontend/src/app/components/upload/upload.component.ts](frontend/src/app/components/upload/upload.component.ts)
  - Spec: [frontend/src/app/components/upload/upload.component.spec.ts](frontend/src/app/components/upload/upload.component.spec.ts)

#### StatementDetailComponent
- **File**: [frontend/src/app/components/statement-detail/statement-detail.component.ts](frontend/src/app/components/statement-detail/statement-detail.component.ts)

#### DashboardComponent
- **Files**:
  - Component: [frontend/src/app/components/dashboard/dashboard.component.ts](frontend/src/app/components/dashboard/dashboard.component.ts)
  - Spec: [frontend/src/app/components/dashboard/dashboard.component.spec.ts](frontend/src/app/components/dashboard/dashboard.component.spec.ts)

#### AuthComponent
- **File**: [frontend/src/app/components/auth/auth.component.ts](frontend/src/app/components/auth/auth.component.ts)

### Test Structure

#### StatementService Spec
- **File**: [frontend/src/app/services/statement.service.spec.ts](frontend/src/app/services/statement.service.spec.ts)
- **Test Framework**: Jasmine + HttpClientTestingModule
- **Tests Covered**:
  - `loads all statements from the statements endpoint` - GET with scope parameter
  - `sends file and metadata as multipart form data during upload` - POST multipart
  - `posts passwords to the unlock endpoint` - POST with password body
  - `downloads CSV as a blob` - GET with blob response type
  - `deletes a statement by id` - DELETE with ID
- **Mock Pattern**: Uses `HttpTestingController` to intercept and verify HTTP requests

#### UploadComponent Spec
- **File**: [frontend/src/app/components/upload/upload.component.spec.ts](frontend/src/app/components/upload/upload.component.spec.ts)
- **Test Framework**: Jasmine (ComponentFixture)
- **Mocks Used**:
  - StatementService (jasmine.SpyObj)
  - Router
  - AuthService
- **Sample Test Data**: `doneStatement` fixture with status="DONE"

### Guards
- **AuthGuard** - [frontend/src/app/guards/auth.guard.ts](frontend/src/app/guards/auth.guard.ts)
- **InternalGuard** - [frontend/src/app/guards/internal.guard.ts](frontend/src/app/guards/internal.guard.ts)

### Interceptors
- **AuthInterceptor** - [frontend/src/app/interceptors/auth.interceptor.ts](frontend/src/app/interceptors/auth.interceptor.ts) - Adds JWT token to requests

---

## 3. PYTHON SERVICE (Flask Microservice)

### Stack & Frameworks
- **Framework**: Flask 3.1.0
- **Language**: Python 3.x
- **Test Framework**: unittest
- **Key Dependencies**:
  - Flask, Flask-CORS
  - PyMuPDF (PDF reading)
  - pdfplumber
  - pandas, OpenPyXL, xlrd (spreadsheet parsing)
  - rapidfuzz (string matching)
  - msoffcrypto-tool (encrypted spreadsheet support)

### Main API Routes

#### Flask App
- **File**: [python-service/app.py](python-service/app.py)
- **Routes**:
  - `GET /health` - Health check
  - `GET /supported-banks` - Return list of bank codes parser recognizes
  - `POST /parse` - Main parsing endpoint (multipart/form-data)

### Core Parser Modules

#### pipeline.py
- **File**: [python-service/bank_parser/pipeline.py](python-service/bank_parser/pipeline.py)
- **Main Function**: `parse_bank_statement(file_path, password=None, bank_hint=None)` 
- **Processes**:
  1. Detects if file is spreadsheet or PDF
  2. Handles password-protected files
  3. Detects bank from letterhead/IFSC codes
  4. Extracts tables from document
  5. Maps columns to standard schema
  6. Validates and categorizes transactions
  7. Computes insights and scorecard
- **Returns**: Dict with dataframe, bank name, validation report, insights, scorecard

#### run.py
- **File**: [python-service/bank_parser/run.py](python-service/bank_parser/run.py)
- **Purpose**: CLI entry point `python run.py <pdf_path>`
- **Outputs**: CSV files and summary to stdout

### Semantic Analysis Modules

#### bank_detector.py
- **File**: [python-service/bank_parser/semantic/bank_detector.py](python-service/bank_parser/semantic/bank_detector.py)
- **Key Functions**:
  - `detect_bank(file_path, password=None)` - Identify bank from document
  - `get_supported_banks()` - Return list of 21+ supported Indian banks
  - `get_bank_overrides(bank_code)` - Get bank-specific parsing rules
  - `normalize_bank_name(name)` - Normalize user input to standard code
- **Supported Banks**: PAYTM, AU_SMALL_FINANCE, HDFC, SBI, ICICI, AXIS, PNB, KOTAK, BOB, CANARA, IDFC, YES, INDUSIND, FEDERAL, IOB, CENTRAL_BANK, UCO, UNION, INDIAN_BANK, PUNJAB_SIND

#### categorizer.py
- **File**: [python-service/bank_parser/semantic/categorizer.py](python-service/bank_parser/semantic/categorizer.py)
- **Classes**: `Category` (Enum with 50+ transaction categories)
- **Key Functions**:
  - `categorize(description, credit=None, debit=None)` - Categorize single transaction
  - `categorize_dataframe(df)` - Add Category column to DataFrame
- **Matching Strategy**: EXACT → SUBSTRING → REGEX with priority ordering
- **Categories**: SALARY, FOOD, GROCERIES, RENT, EMI, TRANSFER_UPI, ATM_WITHDRAWAL, etc.

#### column_mapper.py
- **File**: [python-service/bank_parser/semantic/column_mapper.py](python-service/bank_parser/semantic/column_mapper.py)
- **Standard Schema**: ["Date", "Description", "Debit", "Credit", "Balance", "Reference"]
- **Key Functions**:
  - `map_columns(raw_columns)` - Map raw bank columns to standard schema using fuzzy matching
- **Features**: Handles variations like "Txn Date", "Narration", "Withdrawal", "Cheque No", etc.

### Extraction Modules

#### excel_engine.py
- **File**: [python-service/bank_parser/extractor/excel_engine.py](python-service/bank_parser/extractor/excel_engine.py)
- **Key Functions**:
  - `is_spreadsheet(file_path)` - Check if file is XLSX/XLS/ODS/CSV
  - `check_spreadsheet_encrypted(file_path)` - Detect if XLSX is password-protected
  - `extract_spreadsheet(file_path, password=None)` - Extract tables from spreadsheet
  - `score_table(df)` - Score dataframe likelihood of being transaction table
- **Features**:
  - Auto-detects header rows
  - Scores tables by date patterns, numeric columns, header keywords
  - Handles multiple sheets

#### engine_runner.py
- **File**: [python-service/bank_parser/extractor/engine_runner.py](python-service/bank_parser/extractor/engine_runner.py)
- **Key Function**: `extract_best(file_path, password=None)` - Try multiple PDF extraction methods and return best

### Analytics Modules

#### insights.py
- **File**: [python-service/bank_parser/analytics/insights.py](python-service/bank_parser/analytics/insights.py)
- **Key Functions**:
  - `detect_emis(df)` - Find recurring fixed debits (loan EMIs)
  - `compute_insights(df, statement_period)` - Calculate monthly stats, savings rate, bounce flags
  - `compute_scorecard(df, insights)` - Generate underwriting eligibility score (0-100)
- **Features**:
  - EMI detection with confidence scoring
  - Monthly aggregation (inflows, outflows, net, balance)
  - Bounce detection (negative balance days)
  - Loan eligibility scoring

#### underwriting.py
- **File**: [python-service/bank_parser/analytics/underwriting.py](python-service/bank_parser/analytics/underwriting.py)
- **Purpose**: Underwriting eligibility calculations

### Validation Modules

#### transaction_validator.py
- **File**: [python-service/bank_parser/validators/transaction_validator.py](python-service/bank_parser/validators/transaction_validator.py)
- **Key Functions**:
  - `validate(df)` - Validate transaction dataframe
- **Returns**: Report with total_rows, confidence_score, balance_mismatches, passed status

### Test Files

All tests use `unittest` framework with pandas DataFrames as test fixtures.

#### test_categorizer.py
- **File**: [python-service/tests/test_categorizer.py](python-service/tests/test_categorizer.py)
- **Tests**:
  - Direction-specific rules (credit vs debit)
  - Case insensitivity
  - Unknown default to OTHER
  - Empty description handling
  - NaN value handling
  - DataFrame categorization without mutation

#### test_insights.py
- **File**: [python-service/tests/test_insights.py](python-service/tests/test_insights.py)
- **Tests**:
  - `test_detect_emis_finds_monthly_recurring_debits` - 3+ month patterns
  - `test_detect_emis_handles_no_patterns` - No false positives
  - `test_detect_emis_ignores_credits` - Only debits
  - `test_compute_insights_builds_expected_totals_and_flags` - Monthly aggregation

#### test_column_mapper.py
- **File**: [python-service/tests/test_column_mapper.py](python-service/tests/test_column_mapper.py)

#### test_header_detector.py
- **File**: [python-service/tests/test_header_detector.py](python-service/tests/test_header_detector.py)

#### test_financial_insights.py
- **File**: [python-service/tests/test_financial_insights.py](python-service/tests/test_financial_insights.py)

#### test_transaction_validator.py
- **File**: [python-service/tests/test_transaction_validator.py](python-service/tests/test_transaction_validator.py)

#### test_parser_regressions.py
- **File**: [python-service/tests/test_parser_regressions.py](python-service/tests/test_parser_regressions.py)

#### test_underwriting.py
- **File**: [python-service/tests/test_underwriting.py](python-service/tests/test_underwriting.py)

---

## 4. CURRENT TEST COVERAGE SUMMARY

### Testing Frameworks Used
| Service | Framework | Test Runner | Assertion Library |
|---------|-----------|-------------|-------------------|
| Backend | JUnit 5 | Maven | AssertJ, Hamcrest |
| Frontend | Jasmine 5.1 | Karma 6.4 | Jasmine assertions |
| Python | unittest | pytest / unittest runner | unittest assertions |

### Existing Tests by Module

**Backend**:
- ✅ StatementControllerTest (1+ tests)
- ✅ StatementServiceTest (partial)
- ❌ AuthController - NO TESTS
- ❌ HealthController - NO TESTS
- ❌ AppUserService - NO TESTS

**Frontend**:
- ✅ StatementService.spec.ts (5 tests)
- ✅ UploadComponent.spec.ts (partial)
- ❌ AuthService - NO TESTS
- ❌ DashboardComponent - NO TESTS
- ❌ StatementDetailComponent - NO TESTS
- ❌ AuthComponent - NO TESTS
- ❌ Guards (AuthGuard, InternalGuard) - NO TESTS
- ❌ Interceptors (AuthInterceptor) - NO TESTS

**Python**:
- ✅ test_categorizer.py (5+ tests)
- ✅ test_insights.py (4+ tests)
- ✅ test_column_mapper.py
- ✅ test_header_detector.py
- ✅ test_financial_insights.py
- ✅ test_transaction_validator.py
- ✅ test_parser_regressions.py
- ✅ test_underwriting.py
- ❌ Flask routes (/parse, /health, /supported-banks) - NO TESTS

### Integration Tests
- ❌ End-to-end file upload and parse flow
- ❌ Backend → Python service integration
- ❌ Frontend → Backend API integration
- ❌ Password-protected file unlock workflow
- ❌ Multi-sheet Excel file handling
- ❌ Permission/authorization flows (internal vs user roles)

### Test Coverage Gaps
1. **Backend Auth & Security**: No tests for JWT validation, role-based access, password reset
2. **Frontend Components**: Limited component integration tests
3. **Python Flask Routes**: No HTTP endpoint tests
4. **Error Handling**: Minimal error scenario testing
5. **Data Validation**: Limited negative test cases
6. **File Format Edge Cases**: Password-protected, encrypted, corrupted files

---

## 5. KEY DATA FLOWS

### Upload & Parse Flow
```
Frontend (upload.component) 
  → StatementService.upload() 
  → Backend POST /api/statements 
  → StatementController.upload() 
  → StatementService.uploadAndParse()
  → StatementService.callParser() (HTTP)
  → Python Flask POST /parse
  → pipeline.parse_bank_statement()
  → [bank_detector, categorizer, column_mapper, validators, insights, scorecard]
  → Response → StatementService.applyParserResult()
  → Save to DB
  → Return Statement with transactions
```

### Password-Protected File Flow
```
Initial upload returns "PENDING_PASSWORD" status
Frontend prompts for password
StatementService.unlock(id, password)
Backend POST /api/statements/{id}/unlock
Retry parser with password
[PDF decrypt or spreadsheet re-parse with pwd]
Update statement status to "DONE" or "ERROR"
```

### Authentication Flow
```
AuthComponent → AuthService.login()
POST /api/auth/login
AuthController.login() → AuthenticationManager
AppUserService.loadUserByUsername()
Return JWT + UserSummary
Store in localStorage
AuthInterceptor adds token to all requests
RestoreSession() GET /api/auth/me
```

---

## 6. CRITICAL UNTESTED FUNCTIONS

### Backend
- StatementService.unlockWithPassword() - Critical password handling
- StatementService.callParser() - HTTP integration with Python service
- StatementService.applyParserResult() - Complex response parsing
- AppUserService.resetPassword() - User data modification
- AppUserService.bootstrapInternalUser() - Initialization

### Frontend
- AuthService.restoreSession() - Session recovery on reload
- AuthService.persistSession() - Token storage
- All component lifecycle hooks and error handling

### Python
- parse_bank_statement() - Core parsing logic
- detect_bank() - Bank detection accuracy
- categorize() with all edge cases
- validate() - Balance matching algorithm
- extract_spreadsheet() - Multi-sheet and encrypted handling

---

## 7. REPOSITORY STRUCTURE SUMMARY

```
bank-statement-analyzer/
├── backend/                          # Java/Spring REST API
│   ├── src/main/java/com/bankparser/
│   │   ├── controller/              # 3 REST controllers
│   │   ├── service/                 # 4 services
│   │   ├── model/                   # Data models
│   │   ├── repository/              # Data access
│   │   ├── security/                # JWT, auth
│   │   ├── dto/                     # Transfer objects
│   │   └── config/                  # Spring config
│   ├── src/test/java/               # 2 test files
│   └── pom.xml                      # Maven dependencies
│
├── frontend/                         # Angular 17 SPA
│   ├── src/app/
│   │   ├── services/                # 2 services (1 has spec)
│   │   ├── components/              # 4 components (2 have specs)
│   │   ├── guards/                  # 2 route guards
│   │   ├── interceptors/            # 1 HTTP interceptor
│   │   ├── models/                  # 2 data models
│   │   └── app.routes.ts            # Route config
│   ├── package.json                 # npm dependencies
│   └── angular.json                 # Angular config
│
├── python-service/                  # Flask microservice
│   ├── app.py                       # Flask application
│   ├── bank_parser/
│   │   ├── pipeline.py              # Main parser orchestrator
│   │   ├── run.py                   # CLI entry point
│   │   ├── extractor/               # PDF/Excel extraction (2 modules)
│   │   ├── semantic/                # Bank detect, categorize, map columns
│   │   ├── processors/              # Header detection, reconstruction
│   │   ├── validators/              # Transaction validation
│   │   └── analytics/               # Insights, scoring, underwriting
│   ├── tests/                       # 8 test files (all unittest)
│   └── requirements.txt             # Python dependencies
│
├── docs/                            # Documentation
├── setup.sh, start.sh, stop.sh     # Docker scripts
└── README.md
```

