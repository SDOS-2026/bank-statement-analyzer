import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { StatementService } from '../../services/statement.service';
import { Statement, UploadMetadata } from '../../models/statement.model';

type Step = 'form' | 'uploading' | 'password' | 'done' | 'error';

const BANKS = [
  'AU Small Finance Bank','HDFC Bank','SBI – State Bank of India','ICICI Bank',
  'Axis Bank','Kotak Mahindra Bank','Punjab National Bank','Bank of Baroda',
  'Canara Bank','Union Bank of India','Bank of Allahabad','IDFC First Bank',
  'Yes Bank','IndusInd Bank','Federal Bank','Indian Overseas Bank','Other'
];

const ACCEPTED = '.pdf,.xlsx,.xls,.ods,.csv';

@Component({
  selector: 'app-upload',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
<div class="page" style="max-width:820px">
  <h1 class="page-title">New Statement</h1>
  <p class="page-subtitle">Upload a bank statement — PDF, Excel (.xlsx/.xls), ODS, or CSV</p>

  <!-- STEP: FORM -->
  <ng-container *ngIf="step==='form'">
    <div class="drop-zone" [class.dragover]="dragging"
      (dragover)="$event.preventDefault();dragging=true"
      (dragleave)="dragging=false" (drop)="onDrop($event)" (click)="fi.click()">
      <input #fi type="file" [accept]="accepted" (change)="onFile($event)">
      <div class="drop-icon">📂</div>
      <div class="drop-text">
        <strong>Click to browse</strong> or drag & drop
      </div>
      <div class="drop-text text-sm" style="margin-top:6px;opacity:.7">
        PDF · Excel (xlsx/xls) · ODS · CSV · Max 50 MB
      </div>
      <div class="drop-filename" *ngIf="file">
        <span [style.color]="fileTypeColor()">{{ fileTypeIcon() }}</span>
        &nbsp;{{ file.name }}
        <span class="text-muted text-sm">&nbsp;({{ (file.size/1024).toFixed(0) }} KB)</span>
      </div>
    </div>

    <div class="card mt-16">
      <div class="card-title">Analyst Details</div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Customer Name *</label>
          <input class="form-input" [(ngModel)]="meta.customerName" placeholder="e.g. Saksham Bansal">
        </div>
        <div class="form-group">
          <label class="form-label">Bank Name</label>
          <select class="form-select" [(ngModel)]="meta.bankName">
            <option value="">— Select bank —</option>
            <option *ngFor="let b of banks" [value]="b">{{ b }}</option>
          </select>
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Account Number</label>
          <input class="form-input" [(ngModel)]="meta.accountNumber" placeholder="Last 4 or full">
        </div>
        <div class="form-group">
          <label class="form-label">Statement Period</label>
          <input class="form-input" [(ngModel)]="meta.statementPeriod" placeholder="e.g. Feb 2026">
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Analyst Name</label>
          <input class="form-input" [(ngModel)]="meta.analystName" placeholder="Your name">
        </div>
        <div class="form-group">
          <label class="form-label">Notes</label>
          <input class="form-input" [(ngModel)]="meta.notes" placeholder="Optional">
        </div>
      </div>
      <div class="flex-center gap-12" style="margin-top:8px">
        <button class="btn btn-ghost" (click)="router.navigate(['/dashboard'])">Cancel</button>
        <button class="btn btn-primary ml-auto" (click)="submit()"
          [disabled]="!file || !meta.customerName">
          Parse Statement →
        </button>
      </div>
    </div>

    <div class="card mt-16" *ngIf="error"
      style="background:var(--red-dim);border-color:rgba(255,77,109,.2)">
      <span style="color:var(--red)">⚠ {{ error }}</span>
    </div>
  </ng-container>

  <!-- STEP: UPLOADING -->
  <ng-container *ngIf="step==='uploading'">
    <div class="card" style="text-align:center;padding:64px">
      <div class="spinner" style="width:40px;height:40px;border-width:3px;margin:0 auto 20px"></div>
      <h3 style="font-family:'Inter',sans-serif;font-weight:400;color:var(--text-2);margin-bottom:8px">
        Parsing statement…
      </h3>
      <p class="text-muted text-sm">Extracting transactions, categorising, computing insights.</p>
      <div class="progress-bar mt-16"><div class="progress-fill"></div></div>
    </div>
  </ng-container>

  <!-- STEP: PASSWORD -->
  <ng-container *ngIf="step==='password'">
    <div class="card" style="max-width:420px;margin:0 auto;text-align:center;padding:40px">
      <div style="font-size:2.5rem;margin-bottom:16px">🔐</div>
      <h2 style="margin-bottom:8px">File is Password Protected</h2>
      <p class="text-muted text-sm" style="margin-bottom:24px">
        Enter the password provided by your bank.
      </p>
      <div class="form-group" style="text-align:left">
        <label class="form-label">Password</label>
        <input class="form-input" type="password" [(ngModel)]="password"
          placeholder="Enter password" (keyup.enter)="submitPassword()"
          [style.border-color]="wrongPassword?'var(--red)':''">
        <div style="color:var(--red);font-size:.8rem;margin-top:6px" *ngIf="wrongPassword">
          ✕ Incorrect password. Please try again.
        </div>
      </div>
      <div class="flex-center gap-10" style="margin-top:16px">
        <button class="btn btn-ghost" (click)="reset()">Start Over</button>
        <button class="btn btn-primary ml-auto" (click)="submitPassword()"
          [disabled]="!password||unlocking">
          <span class="spinner" *ngIf="unlocking"
            style="width:14px;height:14px;border-width:2px"></span>
          Unlock →
        </button>
      </div>
    </div>
  </ng-container>

  <!-- STEP: DONE -->
  <ng-container *ngIf="step==='done' && result">
    <div class="card" style="text-align:center;padding:48px">
      <div style="font-size:2.5rem;margin-bottom:16px">✅</div>
      <h2 style="margin-bottom:8px">Extraction Complete</h2>
      <div class="stats-grid" style="margin:20px 0;text-align:left">
        <div class="stat-card">
          <div class="stat-label">Transactions</div>
          <div class="stat-value">{{ result.totalTransactions }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Confidence</div>
          <div class="stat-value green">{{ result.confidence != null ? (result.confidence*100).toFixed(0)+'%' : '—' }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Detected Bank</div>
          <div class="stat-value" style="font-size:.95rem">{{ result.detectedBank || '—' }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Engine</div>
          <div class="stat-value mono" style="font-size:.85rem">{{ result.engineUsed || '—' }}</div>
        </div>
      </div>
      <div class="flex-center gap-12" style="justify-content:center">
        <button class="btn btn-ghost" (click)="reset()">Upload Another</button>
        <button class="btn btn-primary"
          (click)="router.navigate(['/statements', result.id])">
          View Results & Insights →
        </button>
      </div>
    </div>
  </ng-container>

  <!-- STEP: ERROR -->
  <ng-container *ngIf="step==='error'">
    <div class="card" style="text-align:center;padding:48px;border-color:rgba(255,77,109,.3)">
      <div style="font-size:2.5rem;margin-bottom:16px">❌</div>
      <h2 style="margin-bottom:8px">Extraction Failed</h2>
      <p class="text-muted text-sm" style="margin-bottom:8px">{{ error }}</p>
      <button class="btn btn-ghost mt-16" (click)="reset()">Try Again</button>
    </div>
  </ng-container>
</div>
  `
})
export class UploadComponent {
  step: Step = 'form';
  file: File | null = null;
  dragging = false;
  password = '';
  wrongPassword = false;
  unlocking = false;
  error = '';
  result: Statement | null = null;
  statementId: number | null = null;
  accepted = ACCEPTED;
  banks = BANKS;

  meta: UploadMetadata = {
    customerName: '', bankName: '', accountNumber: '',
    statementPeriod: '', analystName: '', notes: ''
  };

  constructor(public router: Router, private svc: StatementService) {}

  onFile(evt: Event) {
    const f = (evt.target as HTMLInputElement).files?.[0];
    if (f) this.file = f;
  }

  onDrop(evt: DragEvent) {
    evt.preventDefault();
    this.dragging = false;
    const f = evt.dataTransfer?.files[0];
    if (f) this.file = f;
    else this.error = 'Could not read dropped file.';
  }

  fileTypeIcon(): string {
    if (!this.file) return '';
    const ext = this.file.name.split('.').pop()?.toLowerCase();
    return { pdf: '📄', xlsx: '📊', xls: '📊', ods: '📊', csv: '📋' }[ext!] ?? '📁';
  }

  fileTypeColor(): string {
    if (!this.file) return '';
    const ext = this.file.name.split('.').pop()?.toLowerCase();
    return ext === 'pdf' ? 'var(--red)' : 'var(--accent)';
  }

  submit() {
    if (!this.file || !this.meta.customerName) return;
    this.step = 'uploading';
    this.error = '';
    this.svc.upload(this.file, this.meta).subscribe({
      next: stmt => this.handleResult(stmt),
      error: e => {
        this.step = 'error';
        this.error = e?.error?.error || 'Upload failed. Is the backend running?';
      }
    });
  }

  handleResult(stmt: Statement) {
    this.statementId = stmt.id;
    if (stmt.status === 'PENDING_PASSWORD') this.step = 'password';
    else if (stmt.status === 'DONE') { this.result = stmt; this.step = 'done'; }
    else { this.step = 'error'; this.error = stmt.errorMessage || 'Extraction failed.'; }
  }

  submitPassword() {
    if (!this.password || !this.statementId) return;
    this.unlocking = true;
    this.wrongPassword = false;
    this.svc.unlock(this.statementId, this.password).subscribe({
      next: stmt => {
        this.unlocking = false;
        if (stmt.status === 'PENDING_PASSWORD') this.wrongPassword = true;
        else this.handleResult(stmt);
      },
      error: () => { this.unlocking = false; this.wrongPassword = true; }
    });
  }

  reset() {
    this.step = 'form'; this.file = null; this.password = '';
    this.wrongPassword = false; this.error = ''; this.result = null;
    this.statementId = null;
    this.meta = { customerName:'', bankName:'', accountNumber:'', statementPeriod:'', analystName:'', notes:'' };
  }
}
