export interface Statement {
  id: number;
  customerName: string;
  bankName: string;
  accountNumber: string;
  statementPeriod: string;
  analystName: string;
  notes: string;
  originalFileName: string;
  fileKey: string;
  fileType: string;
  status: 'PENDING_PASSWORD' | 'PROCESSING' | 'DONE' | 'ERROR';
  detectedBank: string;
  engineUsed: string;
  confidence: number;
  totalTransactions: number;
  balanceMismatches: number;
  debitTotal: number;
  creditTotal: number;
  errorMessage: string;
  insightsJson: string;
  scorecardJson: string;
  createdAt: string;
  updatedAt: string;
}

export interface Transaction {
  id: number;
  date: string;
  description: string;
  debit: number | null;
  credit: number | null;
  balance: number | null;
  reference: string;
  category: string;
  rowIndex: number;
}

export interface UploadMetadata {
  customerName: string;
  bankName: string;
  accountNumber: string;
  statementPeriod: string;
  analystName: string;
  notes: string;
}

export interface MonthlyBreakdown {
  month: string;
  income: number;
  expenses: number;
  emi_outflow: number;
  savings: number;
  savings_rate: number;
  avg_balance: number;
  transaction_count: number;
}

export interface DetectedEMI {
  amount: number;
  frequency: string;
  occurrences: number;
  description_sample: string;
  months_detected: string[];
  confidence: number;
}

export interface FinancialInsights {
  period_start: string;
  period_end: string;
  months_analyzed: number;
  total_income: number;
  total_expenses: number;
  total_emi: number;
  net_savings: number;
  avg_monthly_income: number;
  avg_monthly_expenses: number;
  avg_monthly_savings: number;
  avg_balance: number;
  savings_rate: number;
  emi_burden_ratio: number;
  detected_emis: DetectedEMI[];
  emi_count: number;
  income_stability_score: number;
  income_months: number;
  bounce_count: number;
  low_balance_months: string[];
  negative_balance_months: string[];
  category_totals: Record<string, number>;
  top_expense_categories: { category: string; amount: number; pct: number }[];
  monthly_breakdown: MonthlyBreakdown[];
}

export interface ScorecardComponent {
  name: string;
  score: number;
  max_score: number;
  weight: number;
  reasoning: string;
}

export interface Scorecard {
  final_score: number;
  risk_band: 'EXCELLENT' | 'GOOD' | 'FAIR' | 'POOR' | 'VERY_POOR';
  loan_recommendation: string;
  components: ScorecardComponent[];
  summary: string;
}
