import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { StatementService } from './statement.service';
import { environment } from '../../environments/environment';

describe('StatementService', () => {
  let service: StatementService;
  let http: HttpTestingController;
  const base = `${environment.apiUrl}/api/statements`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
    });
    service = TestBed.inject(StatementService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  // ==================== Original Tests ====================

  it('loads all statements from the statements endpoint', () => {
    service.getAll().subscribe((statements) => {
      expect(statements.length).toBe(1);
      expect(statements[0].customerName).toBe('Asha');
    });

    const req = http.expectOne(`${base}?scope=mine`);
    expect(req.request.method).toBe('GET');
    req.flush([{ id: 1, customerName: 'Asha' }]);
  });

  it('sends file and metadata as multipart form data during upload', () => {
    const file = new File(['sample'], 'sample.pdf', { type: 'application/pdf' });
    const meta = {
      customerName: 'Asha',
      bankName: 'HDFC Bank',
      accountNumber: '1234',
      statementPeriod: 'Jan 2026',
      analystName: 'Tester',
      notes: 'course test',
    };

    service.upload(file, meta).subscribe((statement) => {
      expect(statement.id).toBe(7);
      expect(statement.status).toBe('DONE');
    });

    const req = http.expectOne(base);
    expect(req.request.method).toBe('POST');
    expect(req.request.body instanceof FormData).toBeTrue();
    expect(req.request.body.get('file')).toBe(file);
    expect(req.request.body.get('metadata')).toBe(JSON.stringify(meta));
    req.flush({ id: 7, status: 'DONE' });
  });

  it('posts passwords to the unlock endpoint', () => {
    service.unlock(12, 'secret').subscribe((statement) => {
      expect(statement.status).toBe('PENDING_PASSWORD');
    });

    const req = http.expectOne(`${base}/12/unlock`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ password: 'secret' });
    req.flush({ id: 12, status: 'PENDING_PASSWORD' });
  });

  it('downloads CSV as a blob', () => {
    service.downloadCsv(4).subscribe((blob) => {
      expect(blob instanceof Blob).toBeTrue();
    });

    const req = http.expectOne(`${base}/4/export/csv`);
    expect(req.request.method).toBe('GET');
    expect(req.request.responseType).toBe('blob');
    req.flush(new Blob(['csv']));
  });

  it('deletes a statement by id', () => {
    service.delete(3).subscribe();

    const req = http.expectOne(`${base}/3`);
    expect(req.request.method).toBe('DELETE');
    req.flush(null);
  });

  // ==================== Extended Integration Tests ====================

  it('retrieves statements with custom scope parameter', () => {
    const mockStatements = [
      { id: 1, customerName: 'User1', status: 'DONE' },
      { id: 2, customerName: 'User2', status: 'DONE' },
      { id: 3, customerName: 'Admin1', status: 'PENDING' },
    ];

    service.getAll('all').subscribe((statements) => {
      expect(statements.length).toBe(3);
    });

    const req = http.expectOne(`${base}?scope=all`);
    expect(req.request.method).toBe('GET');
    req.flush(mockStatements);
  });

  it('retrieves single statement by ID', () => {
    const mockStatement = {
      id: 5,
      customerName: 'John Doe',
      status: 'DONE',
      bankName: 'HDFC',
      totalTransactions: 45,
    };

    service.getOne(5).subscribe((statement) => {
      expect(statement.id).toBe(5);
      expect(statement.customerName).toBe('John Doe');
    });

    const req = http.expectOne(`${base}/5`);
    expect(req.request.method).toBe('GET');
    req.flush(mockStatement);
  });

  it('retrieves transactions for a statement', () => {
    const mockTransactions = [
      { id: 1, date: '2024-01-01', description: 'Salary', category: 'INCOME', credit: 50000 },
      { id: 2, date: '2024-01-05', description: 'Rent', category: 'EXPENSES', debit: 15000 },
      { id: 3, date: '2024-01-10', description: 'Groceries', category: 'FOOD', debit: 2000 },
    ];

    service.getTransactions(5).subscribe((transactions) => {
      expect(transactions.length).toBe(3);
      expect(transactions[0].category).toBe('INCOME');
    });

    const req = http.expectOne(`${base}/5/transactions`);
    expect(req.request.method).toBe('GET');
    req.flush(mockTransactions);
  });

  it('retrieves insights for a statement', () => {
    const mockInsights = {
      totalCredit: 150000,
      totalDebit: 45000,
      netIncome: 105000,
      averageTransaction: 3500,
      topCategories: ['INCOME', 'EXPENSES', 'FOOD'],
    };

    service.getInsights(5).subscribe((insights) => {
      expect(insights.totalCredit).toBe(150000);
      expect(insights.topCategories.length).toBe(3);
    });

    const req = http.expectOne(`${base}/5/insights`);
    expect(req.request.method).toBe('GET');
    req.flush(mockInsights);
  });

  it('retrieves scorecard for a statement', () => {
    const mockScorecard = {
      creditScore: 750,
      riskLevel: 'LOW',
      loanEligibility: 'APPROVED',
      monthlyAverage: 7500,
    };

    service.getScorecard(5).subscribe((scorecard) => {
      expect(scorecard.creditScore).toBe(750);
      expect(scorecard.riskLevel).toBe('LOW');
    });

    const req = http.expectOne(`${base}/5/scorecard`);
    expect(req.request.method).toBe('GET');
    req.flush(mockScorecard);
  });

  it('handles password-protected statements', () => {
    const file = new File(['encrypted'], 'protected.pdf');
    const meta = { customerName: 'Protected' };

    service.upload(file, meta).subscribe((response) => {
      expect(response.status).toBe('PENDING_PASSWORD');
    });

    const req = http.expectOne(base);
    req.flush({ id: 102, status: 'PENDING_PASSWORD' });
  });

  it('handles network error on upload', () => {
    const file = new File(['content'], 'test.pdf');
    const meta = { customerName: 'Test' };

    service.upload(file, meta).subscribe(
      () => fail('should have failed'),
      (error) => {
        expect(error).toBeTruthy();
      }
    );

    const req = http.expectOne(base);
    req.error(new ProgressEvent('Network error'));
  });

  it('handles empty transaction list', () => {
    service.getTransactions(20).subscribe((transactions) => {
      expect(transactions.length).toBe(0);
    });

    const req = http.expectOne(`${base}/20/transactions`);
    req.flush([]);
  });

  it('handles statement with special characters in name', () => {
    const mockStatement = {
      id: 25,
      customerName: "O'Brien & Co. (Ltd)",
      status: 'DONE',
    };

    service.getOne(25).subscribe((statement) => {
      expect(statement.customerName).toBe("O'Brien & Co. (Ltd)");
    });

    const req = http.expectOne(`${base}/25`);
    req.flush(mockStatement);
  });

  it('handles error on insights retrieval', () => {
    service.getInsights(99).subscribe(
      () => fail('should have failed'),
      (error) => {
        expect(error.status).toBe(500);
      }
    );

    const req = http.expectOne(`${base}/99/insights`);
    req.flush({ error: 'Analysis failed' }, { status: 500, statusText: 'Internal Server Error' });
  });

  it('handles error on scorecard retrieval', () => {
    service.getScorecard(99).subscribe(
      () => fail('should have failed'),
      (error) => {
        expect(error.status).toBe(500);
      }
    );

    const req = http.expectOne(`${base}/99/scorecard`);
    req.flush({ error: 'Analysis failed' }, { status: 500, statusText: 'Internal Server Error' });
  });

  it('handles large transaction lists', () => {
    const largeTransactionList = Array.from({ length: 1000 }, (_, i) => ({
      id: i,
      date: '2024-01-01',
      description: `Transaction ${i}`,
      category: 'OTHER',
      debit: 100,
    }));

    service.getTransactions(30).subscribe((transactions) => {
      expect(transactions.length).toBe(1000);
    });

    const req = http.expectOne(`${base}/30/transactions`);
    req.flush(largeTransactionList);
  });

  it('handles error when statement not found for deletion', () => {
    service.delete(9999).subscribe(
      () => fail('should have failed'),
      (error) => {
        expect(error.status).toBe(404);
      }
    );

    const req = http.expectOne(`${base}/9999`);
    req.flush({ error: 'Not found' }, { status: 404, statusText: 'Not Found' });
  });

  it('exports CSV with proper content type', () => {
    service.exportCsv(7).subscribe((blob) => {
      expect(blob instanceof Blob).toBeTrue();
    });

    const req = http.expectOne(`${base}/7/export/csv`);
    expect(req.request.responseType).toBe('blob');
    req.flush(new Blob(['Date,Description,Amount']));
  });
});
