import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { StatementService } from '../../services/statement.service';
import { Statement } from '../../models/statement.model';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="page">
      <div class="flex-center gap-16" style="margin-bottom:8px">
        <div>
          <h1 class="page-title">Statements</h1>
          <p class="page-subtitle">All uploaded bank statements and their extraction status</p>
        </div>
        <button class="btn btn-primary ml-auto" (click)="router.navigate(['/upload'])">
          ↑ &nbsp; New Statement
        </button>
      </div>

      <!-- Stats bar -->
      <div class="stats-grid" *ngIf="statements.length > 0">
        <div class="stat-card">
          <div class="stat-label">Total Statements</div>
          <div class="stat-value">{{ statements.length }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Successfully Parsed</div>
          <div class="stat-value green">{{ doneCount }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Pending Password</div>
          <div class="stat-value amber">{{ pendingCount }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Errors</div>
          <div class="stat-value red">{{ errorCount }}</div>
        </div>
      </div>

      <!-- Loading -->
      <div *ngIf="loading" class="flex-center gap-12" style="padding:64px;justify-content:center">
        <div class="spinner"></div>
        <span class="text-muted">Loading statements…</span>
      </div>

      <!-- Empty -->
      <div *ngIf="!loading && statements.length === 0" class="empty-state card">
        <div class="empty-icon">📄</div>
        <h3>No statements yet</h3>
        <p class="text-sm" style="margin-top:8px;margin-bottom:20px">Upload a bank statement PDF to get started</p>
        <button class="btn btn-primary" (click)="router.navigate(['/upload'])">Upload Statement</button>
      </div>

      <!-- Table -->
      <div class="card" *ngIf="!loading && statements.length > 0" style="padding:0;overflow:hidden">
        <div class="data-table-wrap" style="border:none;border-radius:0">
          <table class="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Customer</th>
                <th>Bank</th>
                <th>Period</th>
                <th>Transactions</th>
                <th>Confidence</th>
                <th>Debit Total</th>
                <th>Credit Total</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let s of statements" (click)="open(s)" style="cursor:pointer">
                <td class="text-muted mono">{{ s.id }}</td>
                <td>
                  <div style="font-weight:500">{{ s.customerName || '—' }}</div>
                  <div class="text-muted text-sm">{{ s.analystName ? 'Analyst: ' + s.analystName : '' }}</div>
                </td>
                <td>
                  <div>{{ s.bankName || s.detectedBank || '—' }}</div>
                  <div class="text-muted text-sm mono" *ngIf="s.accountNumber">{{ s.accountNumber }}</div>
                </td>
                <td class="text-muted">{{ s.statementPeriod || '—' }}</td>
                <td class="mono">{{ s.totalTransactions }}</td>
                <td>
                  <ng-container *ngIf="s.confidence != null">
                    <div class="flex-center gap-8">
                      <div class="conf-bar">
                        <div class="conf-fill" [style.width.%]="s.confidence * 100"
                          [style.background]="s.confidence > 0.8 ? 'var(--accent)' : s.confidence > 0.5 ? 'var(--amber)' : 'var(--red)'"></div>
                      </div>
                      <span class="mono text-sm">{{ (s.confidence * 100).toFixed(0) }}%</span>
                    </div>
                  </ng-container>
                  <span *ngIf="s.confidence == null" class="text-muted">—</span>
                </td>
                <td class="amount-debit">{{ s.debitTotal != null ? '₹' + s.debitTotal.toLocaleString('en-IN', {minimumFractionDigits:2}) : '—' }}</td>
                <td class="amount-credit">{{ s.creditTotal != null ? '₹' + s.creditTotal.toLocaleString('en-IN', {minimumFractionDigits:2}) : '—' }}</td>
                <td>
                  <span class="badge" [ngClass]="badgeClass(s.status)">
                    {{ statusLabel(s.status) }}
                  </span>
                </td>
                <td (click)="$event.stopPropagation()">
                  <div class="flex-center gap-8">
                    <button class="btn btn-ghost btn-sm" (click)="open(s)">View</button>
                    <button class="btn btn-danger btn-sm" (click)="deleteStmt(s)">✕</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Toast -->
    <div class="toast success" *ngIf="toast" style="animation: slideUp 0.2s ease">
      ✓ &nbsp; {{ toast }}
    </div>
  `
})
export class DashboardComponent implements OnInit {
  statements: Statement[] = [];
  loading = true;
  toast = '';

  constructor(public router: Router, private svc: StatementService) {}

  ngOnInit() { this.load(); }

  load() {
    this.loading = true;
    this.svc.getAll().subscribe({
      next: s => { this.statements = s; this.loading = false; },
      error: () => { this.loading = false; }
    });
  }

  open(s: Statement) { this.router.navigate(['/statements', s.id]); }

  deleteStmt(s: Statement) {
    if (!confirm(`Delete statement for ${s.customerName || 'this record'}?`)) return;
    this.svc.delete(s.id).subscribe(() => {
      this.statements = this.statements.filter(x => x.id !== s.id);
      this.showToast('Statement deleted');
    });
  }

  showToast(msg: string) {
    this.toast = msg;
    setTimeout(() => this.toast = '', 3000);
  }

  get doneCount()    { return this.statements.filter(s => s.status === 'DONE').length; }
  get pendingCount() { return this.statements.filter(s => s.status === 'PENDING_PASSWORD').length; }
  get errorCount()   { return this.statements.filter(s => s.status === 'ERROR').length; }

  badgeClass(status: string): string {
    return { DONE: 'badge-done', ERROR: 'badge-error', PENDING_PASSWORD: 'badge-pending', PROCESSING: 'badge-processing' }[status] || 'badge-processing';
  }
  statusLabel(status: string): string {
    return { DONE: '✓ Done', ERROR: '✕ Error', PENDING_PASSWORD: '⚿ Locked', PROCESSING: '… Processing' }[status] || status;
  }
}
