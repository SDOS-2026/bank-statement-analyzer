import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Statement, Transaction, UploadMetadata, FinancialInsights, Scorecard } from '../models/statement.model';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class StatementService {
  private base = `${(environment.apiUrl || '').replace(/\/+$/, '')}/api/statements`;

  constructor(private http: HttpClient) {}

  getAll(scope: 'mine' | 'all' = 'mine'): Observable<Statement[]> {
    return this.http.get<Statement[]>(`${this.base}?scope=${scope}`);
  }
  getById(id: number): Observable<Statement> {
    return this.http.get<Statement>(`${this.base}/${id}`);
  }
  upload(file: File, meta: UploadMetadata): Observable<Statement> {
    const form = new FormData();
    form.append('file', file);
    form.append('metadata', JSON.stringify(meta));
    return this.http.post<Statement>(this.base, form);
  }
  unlock(id: number, password: string): Observable<Statement> {
    return this.http.post<Statement>(`${this.base}/${id}/unlock`, { password });
  }
  getTransactions(id: number): Observable<Transaction[]> {
    return this.http.get<Transaction[]>(`${this.base}/${id}/transactions`);
  }
  getInsights(id: number): Observable<FinancialInsights> {
    return this.http.get<FinancialInsights>(`${this.base}/${id}/insights`);
  }
  getScorecard(id: number): Observable<Scorecard> {
    return this.http.get<Scorecard>(`${this.base}/${id}/scorecard`);
  }
  downloadCsv(id: number): Observable<Blob> {
    return this.http.get(`${this.base}/${id}/export/csv`, { responseType: 'blob' });
  }
  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}`);
  }
}
