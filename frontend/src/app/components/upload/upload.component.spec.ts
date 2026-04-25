import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { UploadComponent } from './upload.component';
import { StatementService } from '../../services/statement.service';
import { Router } from '@angular/router';
import { Statement } from '../../models/statement.model';
import { AuthService } from '../../services/auth.service';

const doneStatement = {
  id: 9,
  status: 'DONE',
  totalTransactions: 10,
  confidence: 0.91,
  bankName: 'ICICI Bank',
  detectedBank: 'ICICI',
  engineUsed: 'excel',
} as Statement;

describe('UploadComponent', () => {
  let fixture: ComponentFixture<UploadComponent>;
  let component: UploadComponent;
  let svc: jasmine.SpyObj<StatementService>;

  beforeEach(async () => {
    svc = jasmine.createSpyObj<StatementService>('StatementService', ['upload', 'unlock']);
    svc.upload.and.returnValue(of(doneStatement));
    svc.unlock.and.returnValue(of(doneStatement));
    const auth = jasmine.createSpyObj<AuthService>('AuthService', ['currentUser', 'isInternal']);
    auth.currentUser.and.returnValue({
      id: 1,
      fullName: 'Analyst Tester',
      email: 'analyst@example.com',
      role: 'USER',
      token: 't'
    });
    auth.isInternal.and.returnValue(false);

    await TestBed.configureTestingModule({
      imports: [UploadComponent],
      providers: [
        { provide: StatementService, useValue: svc },
        { provide: Router, useValue: jasmine.createSpyObj<Router>('Router', ['navigate']) },
        { provide: AuthService, useValue: auth },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(UploadComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('detects file type display helpers', () => {
    component.file = new File(['x'], 'statement.xlsx');
    expect(component.fileTypeIcon()).toBe('📊');
    expect(component.fileTypeColor()).toBe('var(--accent)');

    component.file = new File(['x'], 'statement.pdf');
    expect(component.fileTypeIcon()).toBe('📄');
    expect(component.fileTypeColor()).toBe('var(--red)');
  });

  it('requires a file and customer name before upload', () => {
    component.submit();
    expect(svc.upload).not.toHaveBeenCalled();

    component.file = new File(['x'], 'statement.pdf');
    component.meta.customerName = 'Asha';
    component.submit();

    expect(svc.upload).toHaveBeenCalledWith(component.file, component.meta);
    expect(component.step).toBe('done');
    expect(component.result).toBe(doneStatement);
  });

  it('moves password-protected parser responses to password step', () => {
    component.handleResult({ id: 11, status: 'PENDING_PASSWORD' } as Statement);

    expect(component.statementId).toBe(11);
    expect(component.step).toBe('password');
  });

  it('submits passwords and handles wrong password responses', () => {
    component.statementId = 11;
    component.password = 'wrong';
    svc.unlock.and.returnValue(of({ id: 11, status: 'PENDING_PASSWORD' } as Statement));

    component.submitPassword();

    expect(svc.unlock).toHaveBeenCalledWith(11, 'wrong');
    expect(component.wrongPassword).toBeTrue();
  });

  it('surfaces upload errors with backend messages', () => {
    component.file = new File(['x'], 'bad.pdf');
    component.meta.customerName = 'Asha';
    svc.upload.and.returnValue(throwError(() => ({ error: { error: 'Unsupported file' } })));

    component.submit();

    expect(component.step).toBe('error');
    expect(component.error).toBe('Unsupported file');
  });

  it('resets transient upload state', () => {
    component.file = new File(['x'], 'statement.pdf');
    component.password = 'secret';
    component.error = 'Problem';
    component.result = doneStatement;
    component.statementId = 12;

    component.reset();

    expect(component.step).toBe('form');
    expect(component.file).toBeNull();
    expect(component.password).toBe('');
    expect(component.error).toBe('');
    expect(component.result).toBeNull();
    expect(component.statementId).toBeNull();
  });
});
