import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { StatementService } from '../../services/statement.service';
import { Statement, Transaction, FinancialInsights, Scorecard } from '../../models/statement.model';

type Tab = 'transactions' | 'insights' | 'scorecard';

const CATEGORY_COLORS: Record<string, string> = {
  SALARY:'#00e5a0', BUSINESS_INCOME:'#00e5a0', FREELANCE:'#4da6ff',
  INTEREST:'#4da6ff', DIVIDEND:'#4da6ff', REFUND:'#ffb347', CASHBACK:'#ffb347',
  FOOD:'#ff6b6b', GROCERIES:'#ff8c42', TRANSPORT:'#a29bfe', FUEL:'#fd79a8',
  UTILITIES:'#74b9ff', TELECOM:'#55efc4', RENT:'#fdcb6e', EMI:'#e17055',
  INSURANCE:'#fab1a0', INVESTMENT:'#6c5ce7', ENTERTAINMENT:'#fd79a8',
  SHOPPING:'#e84393', HEALTHCARE:'#00cec9', EDUCATION:'#0984e3',
  TRAVEL:'#b2bec3', HOTEL:'#dfe6e9', FEES_CHARGES:'#636e72', TAXES:'#2d3436',
  TRANSFER_UPI:'#dfe6e9', TRANSFER_NEFT:'#dfe6e9', TRANSFER_IMPS:'#dfe6e9',
  TRANSFER_RTGS:'#dfe6e9', TRANSFER_SELF:'#dfe6e9', ATM_WITHDRAWAL:'#b2bec3',
  CASH_DEPOSIT:'#00e5a0', OTHER:'#636e72',
};

@Component({
  selector: 'app-statement-detail',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
<div class="page">
  <button class="btn btn-ghost btn-sm" (click)="router.navigate(['/dashboard'])"
    style="margin-bottom:20px">← Back</button>

  <div *ngIf="loading" class="flex-center gap-12" style="padding:64px;justify-content:center">
    <div class="spinner"></div><span class="text-muted">Loading…</span>
  </div>

  <ng-container *ngIf="!loading && stmt">

    <!-- Header -->
    <div class="flex-center gap-16" style="margin-bottom:24px;flex-wrap:wrap">
      <div>
        <h1 class="page-title">{{ stmt.customerName || 'Statement #'+stmt.id }}</h1>
        <div class="flex-center gap-12 mt-8" style="flex-wrap:wrap">
          <span class="badge" [ngClass]="badgeClass(stmt.status)">{{ statusLabel(stmt.status) }}</span>
          <span class="badge" style="background:var(--surface-2);color:var(--text-2)"
            *ngIf="stmt.fileType">{{ stmt.fileType }}</span>
          <span class="text-muted text-sm">{{ displayBank(stmt) }}</span>
          <span class="text-muted text-sm mono" *ngIf="stmt.accountNumber">{{ stmt.accountNumber }}</span>
          <span class="text-muted text-sm" *ngIf="stmt.statementPeriod">{{ stmt.statementPeriod }}</span>
        </div>
      </div>
      <div class="flex-center gap-8 ml-auto">
        <a *ngIf="stmt.status==='DONE'" [href]="svc.getCsvUrl(stmt.id)"
          class="btn btn-ghost btn-sm" download>↓ CSV</a>
      </div>
    </div>

    <!-- Password panel -->
    <div class="card" *ngIf="stmt.status==='PENDING_PASSWORD'"
      style="max-width:460px;border-color:rgba(255,179,71,.3);margin-bottom:24px">
      <div class="card-title" style="color:var(--amber)">⚿ Password Required</div>
      <div class="form-group">
        <label class="form-label">File Password</label>
        <input class="form-input" type="password" [(ngModel)]="password"
          placeholder="Enter password" (keyup.enter)="unlock()"
          [style.border-color]="wrongPassword?'var(--red)':''">
        <div style="color:var(--red);font-size:.8rem;margin-top:4px" *ngIf="wrongPassword">
          ✕ Incorrect password
        </div>
      </div>
      <button class="btn btn-primary" (click)="unlock()" [disabled]="!password||unlocking">
        <span class="spinner" *ngIf="unlocking" style="width:14px;height:14px;border-width:2px"></span>
        Unlock & Parse
      </button>
      <div *ngIf="unlocking" style="margin-top:16px">
        <p class="text-muted text-sm" style="margin-bottom:8px">
          Decrypting the file and parsing transactions…
        </p>
        <div class="progress-bar"><div class="progress-fill"></div></div>
      </div>
    </div>

    <!-- Error panel -->
    <div class="card" *ngIf="stmt.status==='ERROR'"
      style="border-color:rgba(255,77,109,.3);background:var(--red-dim);margin-bottom:24px">
      <div class="card-title" style="color:var(--red)">✕ Extraction Failed</div>
      <p class="text-muted text-sm">{{ stmt.errorMessage }}</p>
    </div>

    <!-- Key metrics -->
    <div class="stats-grid" *ngIf="stmt.status==='DONE'">
      <div class="stat-card">
        <div class="stat-label">Transactions</div>
        <div class="stat-value">{{ stmt.totalTransactions }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Confidence</div>
        <div class="stat-value"
          [class.green]="(stmt.confidence||0)>.8"
          [class.amber]="(stmt.confidence||0)<=.8&&(stmt.confidence||0)>.5"
          [class.red]="(stmt.confidence||0)<=.5">
          {{ stmt.confidence!=null?(stmt.confidence*100).toFixed(1)+'%':'—' }}
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Total Debits</div>
        <div class="stat-value red">
          {{ stmt.debitTotal!=null?'₹'+fmt(stmt.debitTotal):'—' }}
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Total Credits</div>
        <div class="stat-value green">
          {{ stmt.creditTotal!=null?'₹'+fmt(stmt.creditTotal):'—' }}
        </div>
      </div>
      <div class="stat-card" *ngIf="scorecard">
        <div class="stat-label">Loan Score</div>
        <div class="stat-value" [style.color]="scoreBandColor(scorecard.risk_band)">
          {{ scorecard.final_score }}/100
        </div>
      </div>
      <div class="stat-card" *ngIf="scorecard">
        <div class="stat-label">Risk Band</div>
        <div class="stat-value" style="font-size:.95rem"
          [style.color]="scoreBandColor(scorecard.risk_band)">
          {{ scorecard.risk_band }}
        </div>
      </div>
      <div class="stat-card" *ngIf="insights">
        <div class="stat-label">EMI Burden</div>
        <div class="stat-value"
          [class.green]="(insights.emi_burden_ratio||0)<=20"
          [class.amber]="(insights.emi_burden_ratio||0)>20&&(insights.emi_burden_ratio||0)<=40"
          [class.red]="(insights.emi_burden_ratio||0)>40">
          {{ insights.emi_burden_ratio.toFixed(1) }}%
        </div>
      </div>
    </div>

    <!-- Tab bar -->
    <div class="flex-center gap-4" style="margin-bottom:20px;border-bottom:1px solid var(--border);padding-bottom:0"
      *ngIf="stmt.status==='DONE'">
      <button class="tab-btn" [class.active]="tab==='transactions'"
        (click)="selectTab('transactions')">Transactions</button>
      <button class="tab-btn" [class.active]="tab==='insights'"
        (click)="selectTab('insights')">Financial Insights</button>
      <button class="tab-btn" [class.active]="tab==='scorecard'"
        (click)="selectTab('scorecard')">Underwriting Score</button>
    </div>

    <!-- ═══════════ TAB: TRANSACTIONS ═══════════ -->
    <div *ngIf="tab==='transactions' && stmt.status==='DONE'">
      <div *ngIf="!txnsLoaded && !txnsLoading" style="text-align:center;padding:32px">
        <button class="btn btn-primary" (click)="loadTransactions()">Load Transactions</button>
      </div>
      <div *ngIf="txnsLoading" class="flex-center gap-12" style="padding:32px;justify-content:center">
        <div class="spinner"></div><span class="text-muted">Loading transactions…</span>
      </div>

      <div *ngIf="txnsLoaded" class="card" style="padding:0;overflow:hidden">
        <!-- Controls -->
        <div class="flex-center gap-12" style="padding:14px 20px;border-bottom:1px solid var(--border);flex-wrap:wrap">
          <span class="card-title" style="margin:0">{{ filteredTxns.length }} transactions</span>
          <input class="form-input" [(ngModel)]="search" placeholder="Search description…"
            style="max-width:220px;padding:6px 12px" (ngModelChange)="applyFilters()">
          <select class="form-select" [(ngModel)]="filterCat" style="max-width:180px;padding:6px 12px"
            (ngModelChange)="applyFilters()">
            <option value="">All categories</option>
            <option *ngFor="let c of availableCategories" [value]="c">{{ c }}</option>
          </select>
          <a [href]="svc.getCsvUrl(stmt.id)" class="btn btn-primary btn-sm ml-auto" download>↓ CSV</a>
        </div>

        <!-- Table -->
        <div class="data-table-wrap" style="border:none;max-height:560px;overflow-y:auto">
          <table class="data-table">
            <thead style="position:sticky;top:0;z-index:1">
              <tr>
                <th>#</th><th>Date</th><th style="min-width:260px">Description</th>
                <th>Category</th>
                <th style="text-align:right">Debit (₹)</th>
                <th style="text-align:right">Credit (₹)</th>
                <th style="text-align:right">Balance (₹)</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let t of filteredTxns; let i=index">
                <td class="text-muted mono">{{ i+1 }}</td>
                <td class="mono" style="white-space:nowrap">{{ fmtDate(t.date) }}</td>
                <td style="font-size:.8rem;max-width:320px">{{ t.description }}</td>
                <td>
                  <span class="cat-chip"
                    [style.background]="catColor(t.category)+'22'"
                    [style.color]="catColor(t.category)"
                    [style.border]="'1px solid '+catColor(t.category)+'44'">
                    {{ t.category || 'OTHER' }}
                  </span>
                </td>
                <td class="amount-debit" style="text-align:right">
                  {{ t.debit!=null?fmt(t.debit):'' }}
                </td>
                <td class="amount-credit" style="text-align:right">
                  {{ t.credit!=null?fmt(t.credit):'' }}
                </td>
                <td class="amount-balance" style="text-align:right">
                  {{ t.balance!=null?fmt(t.balance):'—' }}
                </td>
              </tr>
              <tr *ngIf="filteredTxns.length===0">
                <td colspan="7" class="text-muted" style="text-align:center;padding:32px">
                  No matching transactions
                </td>
              </tr>
            </tbody>
            <tfoot *ngIf="filteredTxns.length>0">
              <tr style="background:var(--surface-2)">
                <td colspan="4" style="padding:10px 14px;font-size:.75rem;color:var(--text-2);
                  font-weight:600;text-transform:uppercase;letter-spacing:.05em">Totals</td>
                <td class="amount-debit" style="text-align:right;font-weight:600">
                  {{ fmt(debitSum) }}
                </td>
                <td class="amount-credit" style="text-align:right;font-weight:600">
                  {{ fmt(creditSum) }}
                </td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>

    <!-- ═══════════ TAB: INSIGHTS ═══════════ -->
    <div *ngIf="tab==='insights' && stmt.status==='DONE'">
      <div *ngIf="insightsLoading" class="flex-center gap-12" style="padding:32px;justify-content:center">
        <div class="spinner"></div><span class="text-muted">Computing insights…</span>
      </div>
      <ng-container *ngIf="insights && !insightsLoading">

        <!-- Period + summary strip -->
        <div class="card" style="background:var(--surface-2);margin-bottom:16px">
          <div class="flex-center gap-16" style="flex-wrap:wrap">
            <div>
              <div class="stat-label">Period</div>
              <div style="font-family:'DM Mono',monospace;font-size:.9rem">
                {{ insights.period_start }} → {{ insights.period_end }}
              </div>
            </div>
            <div>
              <div class="stat-label">Months Analysed</div>
              <div class="stat-value">{{ insights.months_analyzed }}</div>
            </div>
            <div>
              <div class="stat-label">Avg Monthly Income</div>
              <div class="stat-value green">₹{{ fmt(insights.avg_monthly_income) }}</div>
            </div>
            <div>
              <div class="stat-label">Avg Monthly Expenses</div>
              <div class="stat-value red">₹{{ fmt(insights.avg_monthly_expenses) }}</div>
            </div>
            <div>
              <div class="stat-label">Net Savings</div>
              <div class="stat-value" [class.green]="insights.net_savings>=0" [class.red]="insights.net_savings<0">
                ₹{{ fmt(insights.net_savings) }}
              </div>
            </div>
            <div>
              <div class="stat-label">Income Stability</div>
              <div class="stat-value"
                [class.green]="insights.income_stability_score>=.75"
                [class.amber]="insights.income_stability_score>=.5&&insights.income_stability_score<.75"
                [class.red]="insights.income_stability_score<.5">
                {{ (insights.income_stability_score*100).toFixed(0) }}%
              </div>
            </div>
          </div>
        </div>

        <!-- Category spend breakdown -->
        <div class="card" style="margin-bottom:16px">
          <div class="card-title">Spend by Category</div>
          <div *ngFor="let cat of insights.top_expense_categories" style="margin-bottom:12px">
            <div class="flex-center" style="margin-bottom:4px">
              <span class="cat-chip"
                [style.background]="catColor(cat.category)+'22'"
                [style.color]="catColor(cat.category)">{{ cat.category }}</span>
              <span class="ml-auto mono text-sm">₹{{ fmt(cat.amount) }}</span>
              <span class="text-muted text-sm" style="width:42px;text-align:right">{{ cat.pct }}%</span>
            </div>
            <div style="height:6px;background:var(--surface-3);border-radius:3px;overflow:hidden">
              <div [style.width.%]="cat.pct" [style.background]="catColor(cat.category)"
                style="height:100%;border-radius:3px;transition:width .5s ease"></div>
            </div>
          </div>
          <div *ngIf="insights.top_expense_categories.length===0" class="text-muted text-sm">
            No category data available.
          </div>
        </div>

        <!-- EMIs detected -->
        <div class="card" style="margin-bottom:16px" *ngIf="insights.emi_count>0">
          <div class="card-title">Detected EMIs ({{ insights.emi_count }})</div>
          <div class="data-table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Amount (₹)</th><th>Frequency</th>
                  <th>Occurrences</th><th>Confidence</th><th>Description Sample</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let e of insights.detected_emis">
                  <td class="amount-debit mono">{{ fmt(e.amount) }}</td>
                  <td><span class="badge badge-pending">{{ e.frequency }}</span></td>
                  <td class="mono">{{ e.occurrences }}×</td>
                  <td>
                    <div class="conf-bar">
                      <div class="conf-fill" [style.width.%]="e.confidence*100"
                        [style.background]="e.confidence>=.7?'var(--accent)':'var(--amber)'"></div>
                    </div>
                    <span class="mono text-sm" style="margin-left:8px">
                      {{ (e.confidence*100).toFixed(0) }}%
                    </span>
                  </td>
                  <td class="text-muted" style="font-size:.78rem;max-width:260px">
                    {{ e.description_sample }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Risk signals -->
        <div class="card" style="margin-bottom:16px"
          *ngIf="insights.bounce_count>0 || insights.negative_balance_months.length>0">
          <div class="card-title" style="color:var(--red)">⚠ Risk Signals</div>
          <div *ngIf="insights.bounce_count>0" style="margin-bottom:8px">
            <span style="color:var(--amber)">Low balance months (< ₹1,000):</span>
            <span class="mono text-sm" style="margin-left:8px">
              {{ insights.low_balance_months.join(', ') }}
            </span>
          </div>
          <div *ngIf="insights.negative_balance_months.length>0">
            <span style="color:var(--red)">Negative balance months:</span>
            <span class="mono text-sm" style="margin-left:8px">
              {{ insights.negative_balance_months.join(', ') }}
            </span>
          </div>
        </div>

        <!-- Monthly breakdown table -->
        <div class="card" style="padding:0;overflow:hidden">
          <div style="padding:14px 20px;border-bottom:1px solid var(--border)">
            <span class="card-title" style="margin:0">Month-by-Month Breakdown</span>
          </div>
          <div class="data-table-wrap" style="border:none">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Month</th><th style="text-align:right">Income</th>
                  <th style="text-align:right">Expenses</th>
                  <th style="text-align:right">EMI</th>
                  <th style="text-align:right">Savings</th>
                  <th style="text-align:right">Savings%</th>
                  <th style="text-align:right">Avg Balance</th>
                  <th style="text-align:right">Txns</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let m of insights.monthly_breakdown">
                  <td class="mono">{{ m.month }}</td>
                  <td class="amount-credit" style="text-align:right">{{ fmt(m.income) }}</td>
                  <td class="amount-debit"  style="text-align:right">{{ fmt(m.expenses) }}</td>
                  <td style="text-align:right;color:var(--amber)" class="mono">
                    {{ m.emi_outflow>0?fmt(m.emi_outflow):'—' }}
                  </td>
                  <td style="text-align:right" class="mono"
                    [style.color]="m.savings>=0?'var(--accent)':'var(--red)'">
                    {{ fmt(m.savings) }}
                  </td>
                  <td style="text-align:right" class="mono"
                    [style.color]="m.savings_rate>=20?'var(--accent)':m.savings_rate>=0?'var(--amber)':'var(--red)'">
                    {{ m.savings_rate.toFixed(1) }}%
                  </td>
                  <td style="text-align:right" class="mono text-muted">
                    {{ m.avg_balance>0?fmt(m.avg_balance):'—' }}
                  </td>
                  <td style="text-align:right" class="mono text-muted">{{ m.transaction_count }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </ng-container>
    </div>

    <!-- ═══════════ TAB: SCORECARD ═══════════ -->
    <div *ngIf="tab==='scorecard' && stmt.status==='DONE'">
      <div *ngIf="scorecardLoading" class="flex-center gap-12"
        style="padding:32px;justify-content:center">
        <div class="spinner"></div><span class="text-muted">Loading scorecard…</span>
      </div>
      <ng-container *ngIf="scorecard && !scorecardLoading">

        <!-- Score hero -->
        <div class="card" style="text-align:center;padding:40px;margin-bottom:16px;
          border-color:{{ scoreBandColor(scorecard.risk_band) }}44">
          <div style="font-size:4rem;font-family:'DM Mono',monospace;font-weight:500;
            color:{{ scoreBandColor(scorecard.risk_band) }}">
            {{ scorecard.final_score }}
            <span style="font-size:1.5rem;color:var(--text-2)">/100</span>
          </div>
          <div class="badge" style="margin:12px auto 16px;display:inline-flex;font-size:.9rem;padding:6px 18px"
            [style.background]="scoreBandColor(scorecard.risk_band)+'22'"
            [style.color]="scoreBandColor(scorecard.risk_band)">
            {{ scorecard.risk_band }}
          </div>
          <p style="color:var(--text-2);max-width:500px;margin:0 auto;font-size:.9rem">
            {{ scorecard.loan_recommendation }}
          </p>
        </div>

        <!-- Score components -->
        <div class="card" style="margin-bottom:16px">
          <div class="card-title">Score Breakdown</div>
          <div *ngFor="let c of scorecard.components" style="margin-bottom:20px">
            <div class="flex-center" style="margin-bottom:6px">
              <span style="font-weight:500;font-size:.88rem">{{ c.name }}</span>
              <span class="ml-auto mono text-sm"
                [style.color]="(c.score/c.max_score)>=.7?'var(--accent)':(c.score/c.max_score)>=.4?'var(--amber)':'var(--red)'">
                {{ c.score }} / {{ c.max_score }}
              </span>
            </div>
            <div style="height:8px;background:var(--surface-3);border-radius:4px;
              overflow:hidden;margin-bottom:6px">
              <div [style.width.%]="(c.score/c.max_score)*100"
                [style.background]="(c.score/c.max_score)>=.7?'var(--accent)':(c.score/c.max_score)>=.4?'var(--amber)':'var(--red)'"
                style="height:100%;border-radius:4px;transition:width .6s ease"></div>
            </div>
            <p class="text-muted text-sm">{{ c.reasoning }}</p>
          </div>
        </div>

        <!-- Summary line -->
        <div class="card" style="background:var(--surface-2)">
          <div class="card-title">Summary</div>
          <p class="mono text-sm" style="color:var(--text-1)">{{ scorecard.summary }}</p>
        </div>
      </ng-container>
    </div>

  </ng-container>
</div>
  `,
  styles: [`
    .tab-btn {
      padding: 10px 18px; background: none; border: none;
      color: var(--text-2); font-size: .88rem; cursor: pointer;
      border-bottom: 2px solid transparent; transition: var(--transition);
      font-family: 'Inter', sans-serif; margin-bottom: -1px;
    }
    .tab-btn:hover { color: var(--text-1); }
    .tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }
    .cat-chip {
      display: inline-block; padding: 2px 8px; border-radius: 12px;
      font-size: .72rem; font-weight: 600; letter-spacing: .04em;
      white-space: nowrap;
    }
  `]
})
export class StatementDetailComponent implements OnInit {
  stmt: Statement | null = null;
  transactions: Transaction[] = [];
  filteredTxns: Transaction[] = [];
  insights: FinancialInsights | null = null;
  scorecard: Scorecard | null = null;
  loading = true;
  txnsLoading = false; txnsLoaded = false;
  insightsLoading = false; scorecardLoading = false;
  tab: Tab = 'transactions';
  search = ''; filterCat = '';
  password = ''; wrongPassword = false; unlocking = false;
  availableCategories: string[] = [];

  constructor(
    public router: Router, public svc: StatementService,
    private route: ActivatedRoute
  ) {}

  ngOnInit() {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.svc.getById(id).subscribe({
      next: s => { this.stmt = s; this.loading = false; },
      error: () => { this.loading = false; }
    });
  }

  selectTab(t: Tab) {
    this.tab = t;
    if (t === 'transactions' && !this.txnsLoaded) this.loadTransactions();
    if (t === 'insights' && !this.insights) this.loadInsights();
    if (t === 'scorecard' && !this.scorecard) this.loadScorecard();
  }

  loadTransactions() {
    if (!this.stmt) return;
    this.txnsLoading = true;
    this.svc.getTransactions(this.stmt.id).subscribe({
      next: t => {
        this.transactions = t;
        this.availableCategories = [...new Set(t.map(x => x.category).filter(Boolean))].sort();
        this.applyFilters();
        this.txnsLoaded = true; this.txnsLoading = false;
      },
      error: () => { this.txnsLoading = false; }
    });
  }

  loadInsights() {
    if (!this.stmt) return;
    this.insightsLoading = true;
    this.svc.getInsights(this.stmt.id).subscribe({
      next: i => { this.insights = i; this.insightsLoading = false; },
      error: () => { this.insightsLoading = false; }
    });
  }

  loadScorecard() {
    if (!this.stmt) return;
    this.scorecardLoading = true;
    this.svc.getScorecard(this.stmt.id).subscribe({
      next: s => { this.scorecard = s; this.scorecardLoading = false; },
      error: () => { this.scorecardLoading = false; }
    });
  }

  applyFilters() {
    let r = this.transactions;
    if (this.search.trim()) {
      const q = this.search.toLowerCase();
      r = r.filter(t =>
        (t.description||'').toLowerCase().includes(q) ||
        (t.reference||'').toLowerCase().includes(q) ||
        (t.date||'').includes(q)
      );
    }
    if (this.filterCat) r = r.filter(t => t.category === this.filterCat);
    this.filteredTxns = r;
  }

  unlock() {
    if (!this.stmt || !this.password) return;
    this.unlocking = true; this.wrongPassword = false;
    this.svc.unlock(this.stmt.id, this.password).subscribe({
      next: s => {
        this.unlocking = false;
        if (s.status === 'PENDING_PASSWORD') this.wrongPassword = true;
        else this.stmt = s;
      },
      error: () => { this.unlocking = false; this.wrongPassword = true; }
    });
  }

  get debitSum()  { return this.filteredTxns.reduce((s,t) => s+(t.debit||0), 0); }
  get creditSum() { return this.filteredTxns.reduce((s,t) => s+(t.credit||0), 0); }

  fmt(v: number | null | undefined): string {
    if (v == null) return '—';
    return v.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  fmtDate(d: string | null): string {
    if (!d) return '—';
    return d.split('T')[0];
  }

  catColor(cat: string): string {
    return CATEGORY_COLORS[cat] ?? '#636e72';
  }

  displayBank(stmt: Statement | null): string {
    return stmt?.bankName || stmt?.detectedBank || '—';
  }

  scoreBandColor(band: string): string {
    return { EXCELLENT:'#00e5a0', GOOD:'#4da6ff', FAIR:'#ffb347',
             POOR:'#ff6b6b', VERY_POOR:'#ff4d6d' }[band] ?? '#8892a4';
  }

  badgeClass(s: string) {
    return { DONE:'badge-done', ERROR:'badge-error',
             PENDING_PASSWORD:'badge-pending', PROCESSING:'badge-processing' }[s] ?? '';
  }
  statusLabel(s: string) {
    return { DONE:'✓ Done', ERROR:'✕ Error',
             PENDING_PASSWORD:'⚿ Locked', PROCESSING:'… Processing' }[s] ?? s;
  }
}
