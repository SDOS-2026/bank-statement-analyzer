import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { DashboardComponent } from './dashboard.component';
import { StatementService } from '../../services/statement.service';
import { Statement } from '../../models/statement.model';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';

const statements: Statement[] = [
  {
    id: 1,
    customerName: 'Asha',
    bankName: 'HDFC Bank',
    accountNumber: '1234',
    statementPeriod: 'Jan 2026',
    analystName: 'Analyst',
    notes: '',
    originalFileName: 'asha.pdf',
    fileKey: '',
    fileType: 'PDF',
    status: 'DONE',
    detectedBank: 'HDFC',
    engineUsed: 'pdfplumber',
    confidence: 0.93,
    totalTransactions: 42,
    balanceMismatches: 0,
    debitTotal: 42000,
    creditTotal: 90000,
    errorMessage: '',
    insightsJson: '',
    scorecardJson: '{"final_score":82,"risk_band":"EXCELLENT"}',
    createdAt: '',
    updatedAt: '',
  },
  {
    id: 2,
    customerName: 'Ravi',
    bankName: '',
    accountNumber: '',
    statementPeriod: '',
    analystName: '',
    notes: '',
    originalFileName: 'ravi.pdf',
    fileKey: '',
    fileType: 'PDF',
    status: 'PENDING_PASSWORD',
    detectedBank: 'PNB',
    engineUsed: '',
    confidence: 0,
    totalTransactions: 0,
    balanceMismatches: 0,
    debitTotal: 0,
    creditTotal: 0,
    errorMessage: '',
    insightsJson: '',
    scorecardJson: '',
    createdAt: '',
    updatedAt: '',
  },
];

describe('DashboardComponent', () => {
  let fixture: ComponentFixture<DashboardComponent>;
  let component: DashboardComponent;
  let svc: jasmine.SpyObj<StatementService>;
  let router: jasmine.SpyObj<Router>;
  let auth: jasmine.SpyObj<AuthService>;

  beforeEach(async () => {
    svc = jasmine.createSpyObj<StatementService>('StatementService', ['getAll', 'delete']);
    router = jasmine.createSpyObj<Router>('Router', ['navigate']);
    auth = jasmine.createSpyObj<AuthService>('AuthService', ['isInternal', 'currentUser']);
    auth.isInternal.and.returnValue(false);
    auth.currentUser.and.returnValue({
      id: 1,
      fullName: 'Test User',
      email: 'test@example.com',
      role: 'USER'
    });
    svc.getAll.and.returnValue(of(statements));
    svc.delete.and.returnValue(of(void 0));

    await TestBed.configureTestingModule({
      imports: [DashboardComponent],
      providers: [
        { provide: StatementService, useValue: svc },
        { provide: Router, useValue: router },
        { provide: AuthService, useValue: auth },
        { provide: ActivatedRoute, useValue: { snapshot: { data: { scope: 'mine' } } } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('loads statements on init and renders the table', () => {
    expect(svc.getAll).toHaveBeenCalledWith('mine');
    expect(component.loading).toBeFalse();
    expect(component.statements.length).toBe(2);
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Asha');
  });

  it('computes status counters for dashboard summary cards', () => {
    expect(component.doneCount).toBe(1);
    expect(component.pendingCount).toBe(1);
    expect(component.errorCount).toBe(0);
  });

  it('parses scorecard JSON safely', () => {
    expect(component.getScore(statements[0])).toBe(82);
    expect(component.getRiskBand(statements[0])).toBe('EXCELLENT');

    const invalid = { ...statements[0], scorecardJson: '{bad json' };
    expect(component.getScore(invalid)).toBeNull();
    expect(component.getRiskBand(invalid)).toBe('');
  });

  it('prefers analyst-provided bank name over detected bank', () => {
    expect(component.displayBank(statements[0])).toBe('HDFC Bank');
    expect(component.displayBank(statements[1])).toBe('PNB');
  });

  it('navigates to a statement detail page', () => {
    component.open(statements[0]);
    expect(router.navigate).toHaveBeenCalledWith(['/statements', 1]);
  });

  it('deletes a statement after confirmation', () => {
    spyOn(window, 'confirm').and.returnValue(true);

    component.del(statements[0]);

    expect(svc.delete).toHaveBeenCalledWith(1);
    expect(component.statements.map((s) => s.id)).toEqual([2]);
    expect(component.toast).toBe('Deleted');
  });
});
