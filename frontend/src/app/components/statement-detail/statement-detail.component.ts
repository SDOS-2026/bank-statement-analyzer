import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { StatementService } from '../../services/statement.service';
import { Statement, Transaction } from '../../models/statement.model';

@Component({
  selector: 'app-statement-detail',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page">

      <!-- Back nav -->
      <button class="btn btn-ghost btn-sm" (click)="router.navigate(['/dashboard'])" style="margin-bottom:20px">
        ← Back to Dashboard
      </button>

      <!-- Loading -->
      <div *ngIf="loading" class="flex-center gap-12" style="padding:64px;justify-content:center">
        <div class="spinner"></div><span class="text-muted">Loading…</span>
      </div>

      <ng-container *ngIf="!loading && stmt">

        <!-- Header -->
        <div class="flex-center gap-16" style="margin-bottom:24px;flex-wrap:wrap">
          <div>
            <h1 class="page-title">{{ stmt.customerName || 'Statement #' + stmt.id }}</h1>
            <div class="flex-center gap-12 mt-8">
              <span class="badge" [ngClass]="badgeClass(stmt.status)">{{ statusLabel(stmt.status) }}</span>
              <span class="text-muted text-sm">{{ stmt.bankName || stmt.detectedBank || '' }}</span>
              <span class="text-muted text-sm mono" *ngIf="stmt.accountNumber">Acc: {{ stmt.accountNumber }}</span>
              <span class="text-muted text-sm" *ngIf="stmt.statementPeriod">{{ stmt.statementPeriod }}</span>
            </div>
          </div>
          <div class="flex-center gap-8 ml-auto">
            <a *ngIf="stmt.status === 'DONE'" [href]="svc.getCsvUrl(stmt.id)"
              class="btn btn-ghost btn-sm" download>
              ↓ Download CSV
            </a>
            <button *ngIf="stmt.status === 'DONE' && !txnsLoaded" class="btn btn-primary"
              (click)="loadTransactions()" [disabled]="txnsLoading">
              <span class="spinner" *ngIf="txnsLoading" style="width:14px;height:14px;border-width:2px"></span>
              View Transactions
            </button>
          </div>
        </div>

        <!-- Password unlock panel -->
        <div class="card" *ngIf="stmt.status === 'PENDING_PASSWORD'"
          style="max-width:460px;border-color:rgba(255,179,71,0.3)">
          <div class="card-title" style="color:var(--amber)">⚿ Password Required</div>
          <p class="text-muted text-sm" style="margin-bottom:16px">
            This PDF is password protected. Enter the password to extract transactions.
          </p>
          <div class="form-group">
            <label class="form-label">PDF Password</label>
            <input class="form-input" type="password" [(ngModel)]="password"
              placeholder="Enter PDF password" (keyup.enter)="unlock()"
              [style.border-color]="wrongPassword ? 'var(--red)' : ''">
            <div style="color:var(--red);font-size:0.8rem;margin-top:4px" *ngIf="wrongPassword">
              ✕ Incorrect password
            </div>
          </div>
          <button class="btn btn-primary" (click)="unlock()" [disabled]="!password || unlocking">
            <span class="spinner" *ngIf="unlocking" style="width:14px;height:14px;border-width:2px"></span>
            Unlock & Parse
          </button>
        </div>

        <!-- Error panel -->
        <div class="card" *ngIf="stmt.status === 'ERROR'"
          style="border-color:rgba(255,77,109,0.3);background:var(--red-dim)">
          <div class="card-title" style="color:var(--red)">✕ Extraction Failed</div>
          <p class="text-muted text-sm">{{ stmt.errorMessage }}</p>
        </div>

        <!-- Stats grid -->
        <div class="stats-grid" *ngIf="stmt.status === 'DONE'">
          <div class="stat-card">
            <div class="stat-label">Transactions</div>
            <div class="stat-value">{{ stmt.totalTransactions }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Confidence</div>
            <div class="stat-value" [class.green]="(stmt.confidence||0)>0.8" [class.amber]="(stmt.confidence||0)<=0.8&&(stmt.confidence||0)>0.5" [class.red]="(stmt.confidence||0)<=0.5">
              {{ stmt.confidence != null ? (stmt.confidence * 100).toFixed(1) + '%' : '—' }}
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Total Debits</div>
            <div class="stat-value red">{{ stmt.debitTotal != null ? '₹' + stmt.debitTotal.toLocaleString('en-IN',{minimumFractionDigits:2}) : '—' }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Total Credits</div>
            <div class="stat-value green">{{ stmt.creditTotal != null ? '₹' + stmt.creditTotal.toLocaleString('en-IN',{minimumFractionDigits:2}) : '—' }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Balance Errors</div>
            <div class="stat-value" [class.red]="(stmt.balanceMismatches||0)>0" [class.green]="(stmt.balanceMismatches||0)===0">
              {{ stmt.balanceMismatches }}
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Engine Used</div>
            <div class="stat-value mono" style="font-size:0.85rem">{{ stmt.engineUsed || '—' }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Detected Bank</div>
            <div class="stat-value" style="font-size:0.95rem">{{ stmt.detectedBank || '—' }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Analyst</div>
            <div class="stat-value" style="font-size:0.95rem">{{ stmt.analystName || '—' }}</div>
          </div>
        </div>

        <!-- Notes -->
        <div class="card mt-16" *ngIf="stmt.notes" style="background:var(--surface-2)">
          <div class="card-title">Notes</div>
          <p class="text-muted text-sm">{{ stmt.notes }}</p>
        </div>

        <!-- Transactions table -->
        <div class="card mt-16" *ngIf="txnsLoaded" style="padding:0;overflow:hidden">
          <div class="flex-center gap-12" style="padding:16px 20px;border-bottom:1px solid var(--border)">
            <span class="card-title" style="margin:0">Transactions</span>
            <span class="badge badge-done" style="margin-left:4px">{{ transactions.length }}</span>
            <!-- Search -->
            <input class="form-input ml-auto" [(ngModel)]="search" placeholder="Search description…"
              style="max-width:240px;padding:6px 12px">
            <a [href]="svc.getCsvUrl(stmt.id)" class="btn btn-primary btn-sm" download>↓ CSV</a>
          </div>

          <div class="data-table-wrap" style="border:none;border-radius:0;max-height:600px;overflow-y:auto">
            <table class="data-table">
              <thead style="position:sticky;top:0;z-index:1">
                <tr>
                  <th>#</th>
                  <th>Date</th>
                  <th style="min-width:300px">Description</th>
                  <th>Reference</th>
                  <th style="text-align:right">Debit (₹)</th>
                  <th style="text-align:right">Credit (₹)</th>
                  <th style="text-align:right">Balance (₹)</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let t of filteredTxns; let i = index">
                  <td class="text-muted mono">{{ i + 1 }}</td>
                  <td class="mono" style="white-space:nowrap">{{ t.date ? t.date.split('T')[0] : '—' }}</td>
                  <td style="font-size:0.8rem;max-width:350px">{{ t.description }}</td>
                  <td class="mono text-muted" style="font-size:0.75rem;max-width:180px;word-break:break-all">{{ t.reference || '—' }}</td>
                  <td class="amount-debit" style="text-align:right">
                    {{ t.debit != null ? t.debit.toLocaleString('en-IN',{minimumFractionDigits:2}) : '' }}
                  </td>
                  <td class="amount-credit" style="text-align:right">
                    {{ t.credit != null ? t.credit.toLocaleString('en-IN',{minimumFractionDigits:2}) : '' }}
                  </td>
                  <td class="amount-balance" style="text-align:right">
                    {{ t.balance != null ? t.balance.toLocaleString('en-IN',{minimumFractionDigits:2}) : '—' }}
                  </td>
                </tr>
                <tr *ngIf="filteredTxns.length === 0">
                  <td colspan="7" class="text-muted" style="text-align:center;padding:32px">No matching transactions</td>
                </tr>
              </tbody>
              <!-- Footer totals -->
              <tfoot *ngIf="filteredTxns.length > 0">
                <tr style="background:var(--surface-2)">
                  <td colspan="4" style="padding:10px 14px;font-size:0.78rem;color:var(--text-2);font-weight:600;letter-spacing:0.05em;text-transform:uppercase">Totals</td>
                  <td class="amount-debit" style="text-align:right;font-weight:600">
                    {{ debitSum.toLocaleString('en-IN',{minimumFractionDigits:2}) }}
                  </td>
                  <td class="amount-credit" style="text-align:right;font-weight:600">
                    {{ creditSum.toLocaleString('en-IN',{minimumFractionDigits:2}) }}
                  </td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      </ng-container>
    </div>
  `
})
export class StatementDetailComponent implements OnInit {
  stmt: Statement | null = null;
  transactions: Transaction[] = [];
  loading = true;
  txnsLoading = false;
  txnsLoaded = false;
  password = '';
  wrongPassword = false;
  unlocking = false;
  search = '';

  constructor(
    public router: Router,
    public svc: StatementService,
    private route: ActivatedRoute
  ) {}

  ngOnInit() {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.svc.getById(id).subscribe({
      next: s => { this.stmt = s; this.loading = false; },
      error: () => { this.loading = false; }
    });
  }

  loadTransactions() {
    if (!this.stmt) return;
    this.txnsLoading = true;
    this.svc.getTransactions(this.stmt.id).subscribe({
      next: t => { this.transactions = t; this.txnsLoaded = true; this.txnsLoading = false; },
      error: () => { this.txnsLoading = false; }
    });
  }

  unlock() {
    if (!this.stmt || !this.password) return;
    this.unlocking = true;
    this.wrongPassword = false;
    this.svc.unlock(this.stmt.id, this.password).subscribe({
      next: s => {
        this.unlocking = false;
        if (s.status === 'PENDING_PASSWORD') { this.wrongPassword = true; }
        else { this.stmt = s; }
      },
      error: () => { this.unlocking = false; this.wrongPassword = true; }
    });
  }

  get filteredTxns(): Transaction[] {
    if (!this.search.trim()) return this.transactions;
    const q = this.search.toLowerCase();
    return this.transactions.filter(t =>
      (t.description || '').toLowerCase().includes(q) ||
      (t.reference || '').toLowerCase().includes(q) ||
      (t.date || '').includes(q)
    );
  }

  get debitSum()  { return this.filteredTxns.reduce((s, t) => s + (t.debit  || 0), 0); }
  get creditSum() { return this.filteredTxns.reduce((s, t) => s + (t.credit || 0), 0); }

  badgeClass(status: string) {
    return { DONE: 'badge-done', ERROR: 'badge-error', PENDING_PASSWORD: 'badge-pending', PROCESSING: 'badge-processing' }[status] || '';
  }
  statusLabel(status: string) {
    return { DONE: '✓ Done', ERROR: '✕ Error', PENDING_PASSWORD: '⚿ Locked', PROCESSING: '… Processing' }[status] || status;
  }
}
