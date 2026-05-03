# Quick Test Execution Guide

## Overview
This document provides quick commands to run the integration test suites for the bank-statement-analyzer project.

## Backend Tests (Java/Spring)

### Run All Backend Tests
```bash
cd backend
mvn test
```

### Run Specific Test Classes
```bash
# AppUserService tests
mvn test -Dtest=AppUserServiceTest

# AuthController tests
mvn test -Dtest=AuthControllerIntegrationTest

# StatementController extended tests
mvn test -Dtest=StatementControllerExtendedIntegrationTest

# Backend error scenario tests
mvn test -Dtest=BackendErrorScenarioIntegrationTest
```

### Run Tests with Coverage Report
```bash
mvn clean test jacoco:report
# Report available at: target/site/jacoco/index.html
```

### Run Tests with Detailed Output
```bash
mvn test -X -e
```

---

## Frontend Tests (Angular 17)

### Run All Frontend Tests
```bash
cd frontend
ng test
```

### Run Frontend Tests in Headless Mode (CI)
```bash
ng test --watch=false --browsers=ChromeHeadless
```

### Run Specific Test File
```bash
# AuthService tests
ng test --include='**/auth.service.spec.ts'

# StatementService tests
ng test --include='**/statement.service.spec.ts'

# Error scenario tests
ng test --include='**/error-scenario.service.spec.ts'
```

### Generate Coverage Report
```bash
ng test --code-coverage --watch=false
# Report available at: coverage/
```

### Run with Debugging
```bash
ng test --browsers=Chrome --watch=true
# Open Chrome DevTools when tests run
```

---

## Python Tests (Flask)

### Run All Python Tests
```bash
cd python-service
python -m pytest tests/ -v
```

### Run Specific Test File
```bash
python -m pytest tests/test_flask_routes.py -v
```

### Run Specific Test Class
```bash
python -m pytest tests/test_flask_routes.py::FlaskRouteIntegrationTest -v
```

### Run Specific Test Method
```bash
python -m pytest tests/test_flask_routes.py::FlaskRouteIntegrationTest::test_health_endpoint_returns_ok_status -v
```

### Generate Coverage Report
```bash
python -m pytest tests/ --cov=python_service --cov-report=html
# Report available at: htmlcov/index.html
```

### Run Tests with Output
```bash
python -m pytest tests/ -v -s
```

---

## Combined Test Run (All Layers)

### Run All Tests Sequentially
```bash
#!/bin/bash

echo "Running Backend Tests..."
cd backend && mvn test && cd ..

echo "Running Frontend Tests..."
cd frontend && ng test --watch=false --browsers=ChromeHeadless && cd ..

echo "Running Python Tests..."
cd python-service && python -m pytest tests/ -v && cd ..

echo "All tests completed!"
```

### Run All Tests with Coverage
```bash
#!/bin/bash

echo "Backend Coverage..."
cd backend && mvn clean test jacoco:report && cd ..

echo "Frontend Coverage..."
cd frontend && ng test --code-coverage --watch=false && cd ..

echo "Python Coverage..."
cd python-service && python -m pytest tests/ --cov=python_service --cov-report=html && cd ..

echo "Coverage reports generated!"
```

---

## Test Count Reference

### Backend
- **AppUserServiceTest**: 30+ tests
- **AuthControllerIntegrationTest**: 20+ tests  
- **StatementControllerExtendedIntegrationTest**: 30+ tests
- **BackendErrorScenarioIntegrationTest**: 35+ tests
- **Total**: 115+ tests

### Frontend
- **auth.service.spec.ts**: 35+ tests
- **statement.service.spec.ts**: 35+ tests
- **error-scenario.service.spec.ts**: 40+ tests
- **Total**: 110+ tests

### Python
- **test_flask_routes.py**: 60+ tests
- **Total**: 60+ tests

### **Grand Total: 280+ tests**

---

## Key Test Categories

### ✅ Authentication & Authorization
- User registration with validation
- Login and logout flows
- Password recovery mechanisms
- Session management
- Role-based access control

### ✅ File Upload & Processing
- File type validation
- Size limit enforcement
- Encryption detection (PDF/Excel)
- Password-protected file handling
- Multi-format support (PDF, Excel, CSV, ODS)

### ✅ Data Retrieval & Export
- Statement listing with scopes
- Transaction retrieval
- Insights and scorecard generation
- CSV export functionality
- Data validation

### ✅ Error Handling
- Network failures
- Invalid input validation
- File not found scenarios
- Size limit violations
- Malformed data handling
- Server errors (500s)

### ✅ Edge Cases
- Null/empty values
- Very long strings
- Special characters (UTF-8)
- Boundary conditions
- Concurrent requests
- Negative/zero amounts

---

## Continuous Integration Setup

### GitHub Actions Example
```yaml
name: Run Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        node-version: [18.x]
        java-version: [17]
        python-version: [3.9]
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Java
        uses: actions/setup-java@v3
        with:
          java-version: ${{ matrix.java-version }}
      
      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: ${{ matrix.node-version }}
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Run Backend Tests
        run: |
          cd backend
          mvn clean test
      
      - name: Run Frontend Tests
        run: |
          cd frontend
          npm install
          npm test -- --watch=false --browsers=ChromeHeadless
      
      - name: Run Python Tests
        run: |
          cd python-service
          pip install -r requirements.txt
          pytest tests/ -v
```

---

## Common Issues & Solutions

### Maven Issues
```bash
# Clear Maven cache
mvn clean
mvn test

# Skip tests during build
mvn clean install -DskipTests
```

### Angular Issues
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Kill running karma server
pkill -f karma
```

### Python Issues
```bash
# Install test dependencies
pip install pytest pytest-cov pytest-mock

# Run with increased verbosity
pytest tests/ -vv
```

---

## Performance Optimization

### Parallel Test Execution (Maven)
```bash
mvn test -DparallelTestClasses=true -DthreadCount=4
```

### Parallel Test Execution (Pytest)
```bash
pip install pytest-xdist
pytest tests/ -n auto
```

---

## Debugging Tests

### Backend (IntelliJ/Eclipse)
```
1. Set breakpoint in test file
2. Right-click test and select "Debug"
3. Step through with F7 (step into) or F8 (step over)
```

### Frontend (Chrome DevTools)
```
1. Run: ng test --browsers=Chrome
2. Open Chrome DevTools (F12)
3. Set breakpoints in Sources tab
4. Tests will pause at breakpoints
```

### Python (PyCharm/VS Code)
```
1. Install pytest plugin
2. Right-click test and select "Run with Python"
3. Use debugging tools to step through
```

---

## Test Maintenance

### Regular Updates
- Update tests when API contracts change
- Add tests for new features
- Remove tests for deprecated features
- Review and optimize slow tests

### Coverage Goals
- **Target**: 80% code coverage
- **Backend**: Focus on service logic
- **Frontend**: Focus on user flows
- **Python**: Focus on parsing logic

### Best Practices
- Keep tests focused and independent
- Use meaningful test names
- Avoid test interdependencies
- Mock external dependencies
- Update documentation with changes

---

## Quick Reference Commands

| Command | Purpose |
|---------|---------|
| `mvn test` | Run all backend tests |
| `ng test` | Run all frontend tests |
| `pytest tests/` | Run all Python tests |
| `mvn clean test jacoco:report` | Backend coverage report |
| `ng test --code-coverage` | Frontend coverage report |
| `pytest --cov=python_service` | Python coverage report |
| `mvn test -Dtest=ClassName` | Run specific Java test |
| `ng test --include='**/file.spec.ts'` | Run specific Angular test |
| `pytest tests/file.py::TestClass` | Run specific Python test |

---

## Support & Documentation

For more information, see:
- [INTEGRATION_TESTS.md](INTEGRATION_TESTS.md) - Detailed test documentation
- Backend: `backend/src/test/java` - Test source files
- Frontend: `frontend/src/app/**/*.spec.ts` - Test source files
- Python: `python-service/tests/` - Test source files
