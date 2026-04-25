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
});
