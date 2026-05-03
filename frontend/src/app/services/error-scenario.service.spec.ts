import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { AuthService } from './auth.service';
import { StatementService } from './statement.service';
import { environment } from '../../environments/environment';

describe('Frontend Error Scenario Integration Tests', () => {
  let authService: AuthService;
  let statementService: StatementService;
  let httpMock: HttpTestingController;
  const apiBase = `${environment.apiUrl}/api`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
    });
    authService = TestBed.inject(AuthService);
    statementService = TestBed.inject(StatementService);
    httpMock = TestBed.inject(HttpTestingController);
    localStorage.clear();
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  // ==================== Authentication Error Scenarios ====================

  it('handles null email on registration', (done) => {
    const registerPayload = {
      fullName: 'John Doe',
      email: null as any,
      password: 'SecurePassword123',
    };

    authService.register(registerPayload).subscribe(
      () => fail('should have failed'),
      (error) => {
        expect(error).toBeTruthy();
        done();
      }
    );

    const req = httpMock.expectOne(`${apiBase}/auth/register`);
    req.flush({ error: 'Email is required' }, { status: 400, statusText: 'Bad Request' });
  });

  it('handles empty email on registration', (done) => {
    const registerPayload = {
      fullName: 'John Doe',
      email: '',
      password: 'SecurePassword123',
    };

    authService.register(registerPayload).subscribe(
      () => fail('should have failed'),
      (error) => {
        expect(error.status).toBe(400);
        done();
      }
    );

    const req = httpMock.expectOne(`${apiBase}/auth/register`);
    req.flush({ error: 'Email is required' }, { status: 400, statusText: 'Bad Request' });
  });

  it('handles extremely long email', (done) => {
    const longEmail = 'a'.repeat(300) + '@example.com';
    const registerPayload = {
      fullName: 'John Doe',
      email: longEmail,
      password: 'SecurePassword123',
    };

    authService.register(registerPayload).subscribe(
      (response) => {
        expect(response.token).toBeTruthy();
        done();
      }
    );

    const req = httpMock.expectOne(`${apiBase}/auth/register`);
    req.flush({
      token: 'jwt_token',
      user: { id: 1, email: longEmail, fullName: 'John Doe', role: 'USER' },
    });
  });

  it('handles special characters in email', (done) => {
    const registerPayload = {
      fullName: 'John Doe',
      email: 'john+test@example.co.uk',
      password: 'SecurePassword123',
    };

    authService.register(registerPayload).subscribe((response) => {
      expect(response.user.email).toContain('+');
      done();
    });

    const req = httpMock.expectOne(`${apiBase}/auth/register`);
    req.flush({
      token: 'jwt_token',
      user: {
        id: 1,
        email: 'john+test@example.co.uk',
        fullName: 'John Doe',
        role: 'USER',
      },
    });
  });

  it('handles network timeout on login', (done) => {
    const loginPayload = {
      email: 'user@example.com',
      password: 'Password123',
    };

    authService.login(loginPayload).subscribe(
      () => fail('should have failed'),
      (error) => {
        expect(error).toBeTruthy();
        done();
      }
    );

    const req = httpMock.expectOne(`${apiBase}/auth/login`);
    req.flush(null, { status: 408, statusText: 'Request Timeout' });
  });

  it('handles server unavailable error', (done) => {
    const loginPayload = {
      email: 'user@example.com',
      password: 'Password123',
    };

    authService.login(loginPayload).subscribe(
      () => fail('should have failed'),
      (error) => {
        expect(error.status).toBe(503);
        done();
      }
    );

    const req = httpMock.expectOne(`${apiBase}/auth/login`);
    req.flush({ error: 'Service Unavailable' }, { status: 503, statusText: 'Service Unavailable' });
  });

  it('handles malformed server response', (done) => {
    authService.login({ email: 'user@example.com', password: 'password' }).subscribe(
      () => fail('should have failed'),
      (error) => {
        expect(error).toBeTruthy();
        done();
      }
    );

    const req = httpMock.expectOne(`${apiBase}/auth/login`);
    req.flush('Not valid JSON', { status: 502, statusText: 'Bad Gateway' });
  });

  // ==================== Password Error Scenarios ====================

  it('handles extremely short password', (done) => {
    const registerPayload = {
      fullName: 'John Doe',
      email: 'john@example.com',
      password: '1',
    };

    authService.register(registerPayload).subscribe(
      () => fail('should have failed'),
      (error) => {
        expect(error.status).toBe(400);
        done();
      }
    );

    const req = httpMock.expectOne(`${apiBase}/auth/register`);
    req.flush(
      { error: 'Password must be at least 8 characters.' },
      { status: 400, statusText: 'Bad Request' }
    );
  });

  it('handles password reset with null email', (done) => {
    const forgotPayload = {
      email: null as any,
      fullName: 'User Name',
      newPassword: 'NewPassword123',
    };

    authService.forgotPassword(forgotPayload).subscribe(
      () => fail('should have failed'),
      (error) => {
        expect(error).toBeTruthy();
        done();
      }
    );

    const req = httpMock.expectOne(`${apiBase}/auth/forgot-password`);
    req.flush({ error: 'Email is required' }, { status: 400, statusText: 'Bad Request' });
  });

  // ==================== Statement Upload Error Scenarios ====================

  it('handles file upload with null file', (done) => {
    const metadata = { customerName: 'Test User' };

    statementService.upload(null as any, metadata).subscribe(
      () => fail('should have failed'),
      (error) => {
        expect(error).toBeTruthy();
        done();
      }
    );

    const req = httpMock.expectOne(`${environment.apiUrl}/api/statements`);
    req.flush({ error: 'File is required' }, { status: 400, statusText: 'Bad Request' });
  });

  it('handles file upload with extremely large file', (done) => {
    const largeFile = new File(['x'.repeat(60 * 1024 * 1024)], 'large.pdf');
    const metadata = { customerName: 'Test' };

    statementService.upload(largeFile, metadata).subscribe(
      () => fail('should have failed'),
      (error) => {
        expect(error.status).toBe(413);
        done();
      }
    );

    const req = httpMock.expectOne(`${environment.apiUrl}/api/statements`);
    req.flush(
      { error: 'File too large' },
      { status: 413, statusText: 'Payload Too Large' }
    );
  });

  it('handles file upload with unsupported file type', (done) => {
    const unsupportedFile = new File(['content'], 'document.docx');
    const metadata = { customerName: 'Test' };

    statementService.upload(unsupportedFile, metadata).subscribe(
      () => fail('should have failed'),
      (error) => {
        expect(error.status).toBe(400);
        done();
      }
    );

    const req = httpMock.expectOne(`${environment.apiUrl}/api/statements`);
    req.flush(
      { error: 'Unsupported file type' },
      { status: 400, statusText: 'Bad Request' }
    );
  });

  it('handles file upload network interruption', (done) => {
    const file = new File(['content'], 'statement.pdf');
    const metadata = { customerName: 'Test' };

    statementService.upload(file, metadata).subscribe(
      () => fail('should have failed'),
      (error) => {
        expect(error).toBeTruthy();
        done();
      }
    );

    const req = httpMock.expectOne(`${environment.apiUrl}/api/statements`);
    req.error(new ProgressEvent('Network error'));
  });

  // ==================== Statement Retrieval Error Scenarios ====================

  it('handles retrieval of non-existent statement', (done) => {
    statementService.getOne(99999).subscribe(
      () => fail('should have failed'),
      (error) => {
        expect(error.status).toBe(404);
        done();
      }
    );

    const req = httpMock.expectOne(`${environment.apiUrl}/api/statements/99999`);
    req.flush({ error: 'Not found' }, { status: 404, statusText: 'Not Found' });
  });

  it('handles retrieval of statement with database error', (done) => {
    statementService.getOne(1).subscribe(
      () => fail('should have failed'),
      (error) => {
        expect(error.status).toBe(500);
        done();
      }
    );

    const req = httpMock.expectOne(`${environment.apiUrl}/api/statements/1`);
    req.flush(
      { error: 'Database error' },
      { status: 500, statusText: 'Internal Server Error' }
    );
  });

  it('handles retrieval of transactions with empty response', () => {
    statementService.getTransactions(1).subscribe((transactions) => {
      expect(transactions.length).toBe(0);
    });

    const req = httpMock.expectOne(`${environment.apiUrl}/api/statements/1/transactions`);
    req.flush([]);
  });

  it('handles retrieval of transactions with null values', () => {
    const transactionsWithNulls = [
      {
        id: 1,
        date: null,
        description: null,
        category: null,
        debit: null,
        credit: null,
      },
    ];

    statementService.getTransactions(1).subscribe((transactions) => {
      expect(transactions[0].date).toBeNull();
      expect(transactions[0].description).toBeNull();
    });

    const req = httpMock.expectOne(`${environment.apiUrl}/api/statements/1/transactions`);
    req.flush(transactionsWithNulls);
  });

  // ==================== Export Error Scenarios ====================

  it('handles CSV export for non-existent statement', (done) => {
    statementService.exportCsv(99999).subscribe(
      () => fail('should have failed'),
      (error) => {
        expect(error.status).toBe(404);
        done();
      }
    );

    const req = httpMock.expectOne(`${environment.apiUrl}/api/statements/99999/export/csv`);
    req.flush(null, { status: 404, statusText: 'Not Found' });
  });

  it('handles CSV export with server error', (done) => {
    statementService.exportCsv(1).subscribe(
      () => fail('should have failed'),
      (error) => {
        expect(error.status).toBe(500);
        done();
      }
    );

    const req = httpMock.expectOne(`${environment.apiUrl}/api/statements/1/export/csv`);
    req.flush(new Blob(['Export failed']), { status: 500, statusText: 'Internal Server Error' });
  });

  // ==================== Session Management Error Scenarios ====================

  it('handles session restore with expired token', (done) => {
    const expiredToken = 'expired_jwt_token';
    localStorage.setItem('finparse.auth.token', expiredToken);

    authService.restoreSession().then(() => {
      expect(localStorage.getItem('finparse.auth.token')).toBeNull();
      expect(authService.currentUser()).toBeNull();
      done();
    });

    const req = httpMock.expectOne(`${apiBase}/auth/me`);
    req.flush(
      { error: 'Token expired' },
      { status: 401, statusText: 'Unauthorized' }
    );
  });

  it('handles session restore with corrupted token', (done) => {
    const corruptedToken = 'not.a.valid.jwt';
    localStorage.setItem('finparse.auth.token', corruptedToken);

    authService.restoreSession().then(() => {
      expect(localStorage.getItem('finparse.auth.token')).toBeNull();
      done();
    });

    const req = httpMock.expectOne(`${apiBase}/auth/me`);
    req.flush(
      { error: 'Invalid token' },
      { status: 401, statusText: 'Unauthorized' }
    );
  });

  // ==================== Insights and Scorecard Error Scenarios ====================

  it('handles insights retrieval for statement without transactions', (done) => {
    statementService.getInsights(1).subscribe((insights) => {
      expect(insights).toBeTruthy();
      done();
    });

    const req = httpMock.expectOne(`${environment.apiUrl}/api/statements/1/insights`);
    req.flush({
      totalCredit: 0,
      totalDebit: 0,
      netIncome: 0,
      averageTransaction: 0,
    });
  });

  it('handles scorecard retrieval with analysis engine error', (done) => {
    statementService.getScorecard(1).subscribe(
      () => fail('should have failed'),
      (error) => {
        expect(error.status).toBe(500);
        done();
      }
    );

    const req = httpMock.expectOne(`${environment.apiUrl}/api/statements/1/scorecard`);
    req.flush(
      { error: 'Analysis engine error' },
      { status: 500, statusText: 'Internal Server Error' }
    );
  });

  // ==================== Edge Cases ====================

  it('handles unlock with very long password', (done) => {
    const longPassword = 'a'.repeat(1000);

    statementService.unlock(1, longPassword).subscribe((statement) => {
      expect(statement.id).toBe(1);
      done();
    });

    const req = httpMock.expectOne(`${environment.apiUrl}/api/statements/1/unlock`);
    req.flush({ id: 1, status: 'DONE' });
  });

  it('handles unlock with special characters in password', (done) => {
    const specialPassword = '!@#$%^&*()[]{}';

    statementService.unlock(1, specialPassword).subscribe((statement) => {
      expect(statement.id).toBe(1);
      done();
    });

    const req = httpMock.expectOne(`${environment.apiUrl}/api/statements/1/unlock`);
    req.flush({ id: 1, status: 'DONE' });
  });

  it('handles delete with negative statement ID', (done) => {
    statementService.delete(-1).subscribe(
      () => fail('should have failed'),
      (error) => {
        expect(error).toBeTruthy();
        done();
      }
    );

    const req = httpMock.expectOne(`${environment.apiUrl}/api/statements/-1`);
    req.flush({ error: 'Invalid ID' }, { status: 400, statusText: 'Bad Request' });
  });

  it('handles concurrent requests to same endpoint', () => {
    statementService.getAll().subscribe();
    statementService.getAll().subscribe();
    statementService.getAll().subscribe();

    const requests = httpMock.match(`${environment.apiUrl}/api/statements?scope=mine`);
    expect(requests.length).toBe(3);

    requests.forEach((req) => req.flush([]));
  });

  it('handles response with special UTF-8 characters', () => {
    const statementWithSpecialChars = {
      id: 1,
      customerName: 'राज कुमार',
      bankName: '中国银行',
      status: 'DONE',
    };

    statementService.getOne(1).subscribe((statement) => {
      expect(statement.customerName).toBe('राज कुमार');
      expect(statement.bankName).toBe('中国银行');
    });

    const req = httpMock.expectOne(`${environment.apiUrl}/api/statements/1`);
    req.flush(statementWithSpecialChars);
  });
});
