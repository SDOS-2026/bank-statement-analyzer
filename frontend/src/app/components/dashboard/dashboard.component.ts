import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';

import { Statement } from '../../models/statement.model';
import { AuthService } from '../../services/auth.service';
import { StatementService } from '../../services/statement.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  template: `
<div class="page">
  <div class="flex-center gap-16" style="margin-bottom:8px">
    <div>
      <h1 class="page-title">{{ dashboardTitle }}</h1>
      <p class="page-subtitle">{{ dashboardSubtitle }}</p>
    </div>
    <button class="btn btn-primary ml-auto" (click)="router.navigate(['/upload'])">
      ↑ &nbsp;New Statement
    </button>
  </div>

  <div class="stats-grid" *ngIf="statements.length>0">
    <div class="stat-card">
      <div class="stat-label">Total</div>
      <div class="stat-value">{{ statements.length }}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Parsed</div>
      <div class="stat-value green">{{ doneCount }}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Locked</div>
      <div class="stat-value amber">{{ pendingCount }}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Errors</div>
      <div class="stat-value red">{{ errorCount }}</div>
    </div>
  </div>

  <div *ngIf="loading" class="flex-center gap-12" style="padding:64px;justify-content:center">
    <div class="spinner"></div><span class="text-muted">Loading…</span>
  </div>

  <div *ngIf="!loading && statements.length===0" class="empty-state card">
    <div class="empty-icon">📄</div>
    <h3>No statements yet</h3>
    <p class="text-sm" style="margin:8px 0 20px">
      Upload a PDF or Excel bank statement to get started
    </p>
    <button class="btn btn-primary" (click)="router.navigate(['/upload'])">
      Upload Statement
    </button>
  </div>

  <div class="card" *ngIf="!loading && statements.length>0" style="padding:0;overflow:hidden">
    <div class="data-table-wrap" style="border:none;border-radius:0">
      <table class="data-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Customer</th>
            <th>Bank</th>
            <th>Type</th>
            <th>Txns</th>
            <th>Score</th>
            <th>Confidence</th>
            <th>Debits</th>
            <th>Credits</th>
            <th>Status</th>
            <th *ngIf="scope==='all'">Uploaded By</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let s of statements" (click)="open(s)" style="cursor:pointer">
            <td class="text-muted mono">{{ s.id }}</td>
            <td>
              <div style="font-weight:500">{{ s.customerName||'—' }}</div>
              <div class="text-muted text-sm" *ngIf="s.analystName">{{ s.analystName }}</div>
            </td>
            <td>
              <div>{{ displayBank(s) }}</div>
              <div class="text-muted text-sm mono" *ngIf="s.accountNumber">{{ s.accountNumber }}</div>
            </td>
            <td>
              <span class="badge"
                [style.background]="s.fileType==='PDF'?'var(--red-dim)':'var(--accent-dim)'"
                [style.color]="s.fileType==='PDF'?'var(--red)':'var(--accent)'">
                {{ s.fileType||'PDF' }}
              </span>
            </td>
            <td class="mono">{{ s.totalTransactions }}</td>
            <td>
              <ng-container *ngIf="getScore(s) as sc">
                <span style="font-family:'DM Mono',monospace;font-weight:500" [style.color]="scoreBandColor(getRiskBand(s))">
                  {{ sc }}/100
                </span>
                <div style="font-size:.7rem;margin-top:2px" [style.color]="scoreBandColor(getRiskBand(s))">
                  {{ getRiskBand(s) }}
                </div>
              </ng-container>
              <span *ngIf="!getScore(s)" class="text-muted">—</span>
            </td>
            <td>
              <ng-container *ngIf="s.confidence!=null">
                <div class="flex-center gap-8">
                  <div class="conf-bar">
                    <div class="conf-fill"
                      [style.width.%]="s.confidence*100"
                      [style.background]="s.confidence>.8?'var(--accent)':s.confidence>.5?'var(--amber)':'var(--red)'">
                    </div>
                  </div>
                  <span class="mono text-sm">{{ (s.confidence*100).toFixed(0) }}%</span>
                </div>
              </ng-container>
              <span *ngIf="s.confidence==null" class="text-muted">—</span>
            </td>
            <td class="amount-debit">{{ s.debitTotal!=null?'₹'+fmt(s.debitTotal):'—' }}</td>
            <td class="amount-credit">{{ s.creditTotal!=null?'₹'+fmt(s.creditTotal):'—' }}</td>
            <td>
              <span class="badge" [ngClass]="badgeClass(s.status)">{{ statusLabel(s.status) }}</span>
            </td>
            <td *ngIf="scope==='all'">
              <div>{{ s.ownerName || '—' }}</div>
              <div class="text-muted text-sm" *ngIf="s.ownerEmail">{{ s.ownerEmail }}</div>
            </td>
            <td (click)="$event.stopPropagation()">
              <div class="flex-center gap-8">
                <button class="btn btn-ghost btn-sm" (click)="open(s)">View</button>
                <button class="btn btn-danger btn-sm" (click)="del(s)">✕</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

<div class="toast success" *ngIf="toast">✓ &nbsp;{{ toast }}</div>
  `
})
export class DashboardComponent implements OnInit {
  statements: Statement[] = [];
  loading = true;
  toast = '';
  scope: 'mine' | 'all' = 'mine';

  constructor(
    public router: Router,
    private route: ActivatedRoute,
    private svc: StatementService,
    public auth: AuthService
  ) {}

  ngOnInit() {
    this.scope = this.route.snapshot.data['scope'] === 'all' ? 'all' : 'mine';
    this.load();
  }

  load() {
    this.loading = true;
    this.svc.getAll(this.scope).subscribe({
      next: s => { this.statements = s; this.loading = false; },
      error: () => { this.loading = false; }
    });
  }

  open(s: Statement) {
    this.router.navigate(['/statements', s.id]);
  }

  del(s: Statement) {
    if (!confirm(`Delete statement for ${s.customerName || 'this record'}?`)) return;
    this.svc.delete(s.id).subscribe(() => {
      this.statements = this.statements.filter(x => x.id !== s.id);
      this.showToast('Deleted');
    });
  }

  showToast(msg: string) {
    this.toast = msg;
    setTimeout(() => this.toast = '', 3000);
  }

  getScore(s: Statement): number | null {
    if (!s.scorecardJson) return null;
    try { return JSON.parse(s.scorecardJson).final_score ?? null; }
    catch { return null; }
  }

  getRiskBand(s: Statement): string {
    if (!s.scorecardJson) return '';
    try { return JSON.parse(s.scorecardJson).risk_band ?? ''; }
    catch { return ''; }
  }

  scoreBandColor(band: string): string {
    return { EXCELLENT:'#00e5a0', GOOD:'#4da6ff', FAIR:'#ffb347', POOR:'#ff6b6b', VERY_POOR:'#ff4d6d' }[band] ?? '#8892a4';
  }

  fmt(v: number): string {
    return v.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  displayBank(s: Statement): string {
    return s.bankName || s.detectedBank || '—';
  }

  get dashboardTitle() {
    return this.scope === 'all' ? 'Internal Dashboard' : 'My Statements';
  }

  get dashboardSubtitle() {
    return this.scope === 'all'
      ? 'All uploaded statements across users, visible only to internal reviewers'
      : 'Only your own uploaded bank statements and analysis';
  }

  get doneCount() { return this.statements.filter(s => s.status === 'DONE').length; }
  get pendingCount() { return this.statements.filter(s => s.status === 'PENDING_PASSWORD').length; }
  get errorCount() { return this.statements.filter(s => s.status === 'ERROR').length; }

  badgeClass(s: string) {
    return { DONE:'badge-done', ERROR:'badge-error', PENDING_PASSWORD:'badge-pending', PROCESSING:'badge-processing' }[s] ?? '';
  }

  statusLabel(s: string) {
    return { DONE:'✓ Done', ERROR:'✕ Error', PENDING_PASSWORD:'⚿ Locked', PROCESSING:'… Processing' }[s] ?? s;
  }
}
