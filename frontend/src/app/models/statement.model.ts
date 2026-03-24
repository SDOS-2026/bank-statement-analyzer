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
  status: 'PENDING_PASSWORD' | 'PROCESSING' | 'DONE' | 'ERROR';
  detectedBank: string;
  engineUsed: string;
  confidence: number;
  totalTransactions: number;
  balanceMismatches: number;
  debitTotal: number;
  creditTotal: number;
  errorMessage: string;
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
