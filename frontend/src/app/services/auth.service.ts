import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../environments/environment';
import { AuthenticatedUser, AuthResponse } from '../models/auth.model';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly tokenKey = 'finparse.auth.token';
  readonly user = signal<AuthenticatedUser | null>(null);
  private readonly apiRoot = (environment.apiUrl || '').replace(/\/+$/, '');
  private readonly base = `${this.apiRoot}/api/auth`;

  constructor(private http: HttpClient) {}

  currentUser(): AuthenticatedUser | null {
    return this.user();
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  isInternal(): boolean {
    return this.user()?.role === 'INTERNAL';
  }

  getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }

  async restoreSession(): Promise<void> {
    const token = this.getToken();
    if (!token) {
      this.user.set(null);
      return;
    }
    try {
      const me = await firstValueFrom(this.http.get<AuthenticatedUser>(`${this.base}/me`));
      this.user.set(me);
    } catch {
      this.logout();
    }
  }

  login(payload: { email: string; password: string; }) {
    return this.http.post<AuthResponse>(`${this.base}/login`, payload);
  }

  register(payload: { fullName: string; email: string; password: string; }) {
    return this.http.post<AuthResponse>(`${this.base}/register`, payload);
  }

  forgotPassword(payload: { email: string; fullName: string; newPassword: string; }) {
    return this.http.post<{ message: string }>(`${this.base}/forgot-password`, payload);
  }

  persistSession(response: AuthResponse) {
    localStorage.setItem(this.tokenKey, response.token);
    this.user.set(response.user);
  }

  logout() {
    localStorage.removeItem(this.tokenKey);
    this.user.set(null);
  }
}
