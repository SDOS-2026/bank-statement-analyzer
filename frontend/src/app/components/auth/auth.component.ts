import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { AuthService } from '../../services/auth.service';

type AuthMode = 'login' | 'register';

@Component({
  selector: 'app-auth',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="auth-page">
      <div class="auth-card">
        <div class="brand">
          <div class="brand-mark">FP</div>
          <div>
            <h1>FinParse</h1>
            <p>Secure statement analysis for users and internal reviewers</p>
          </div>
        </div>

        <div class="toggle">
          <button [class.active]="mode==='login'" (click)="mode='login'">Sign in</button>
          <button [class.active]="mode==='register'" (click)="mode='register'">Create account</button>
        </div>

        <div class="form-group" *ngIf="mode==='register'">
          <label class="form-label">Full name</label>
          <input class="form-input" [(ngModel)]="registerForm.fullName" placeholder="Your name">
        </div>

        <div class="form-group">
          <label class="form-label">Email</label>
          <input class="form-input" [(ngModel)]="email" type="email" placeholder="you@example.com">
        </div>

        <div class="form-group">
          <label class="form-label">Password</label>
          <input class="form-input" [(ngModel)]="password" type="password" placeholder="Minimum 8 characters" (keyup.enter)="submit()">
        </div>

        <div class="form-group" *ngIf="mode==='register'">
          <label class="form-label">Confirm password</label>
          <input class="form-input" [(ngModel)]="confirmPassword" type="password" placeholder="Repeat password" (keyup.enter)="submit()">
        </div>

        <div class="error" *ngIf="error">{{ error }}</div>

        <button class="submit-btn" (click)="submit()" [disabled]="loading">
          {{ loading ? 'Please wait...' : mode==='login' ? 'Sign in' : 'Create account' }}
        </button>

        <p class="helper" *ngIf="mode==='register'">
          New accounts are created as user dashboards only. Internal reviewer accounts are bootstrapped from backend environment variables.
        </p>
      </div>
    </div>
  `,
  styles: [`
    .auth-page{min-height:100vh;display:grid;place-items:center;padding:24px;background:
      radial-gradient(circle at top left, rgba(0,229,160,.12), transparent 35%),
      radial-gradient(circle at bottom right, rgba(77,166,255,.14), transparent 40%),
      linear-gradient(180deg, #f7fafc 0%, #eef3f8 100%)}
    .auth-card{width:min(100%, 440px);background:#fff;border:1px solid rgba(15,23,42,.08);border-radius:24px;padding:28px;box-shadow:0 20px 60px rgba(15,23,42,.08)}
    .brand{display:flex;gap:14px;align-items:center;margin-bottom:20px}
    .brand-mark{width:46px;height:46px;border-radius:14px;background:#0f172a;color:#fff;display:grid;place-items:center;font-weight:800}
    h1{margin:0;font-size:1.6rem;color:#0f172a}
    p{margin:4px 0 0;color:#64748b}
    .toggle{display:flex;gap:8px;background:#f1f5f9;padding:6px;border-radius:14px;margin:18px 0}
    .toggle button{flex:1;border:none;background:transparent;padding:10px 12px;border-radius:10px;font-weight:700;color:#475569;cursor:pointer}
    .toggle button.active{background:#fff;color:#0f172a;box-shadow:0 2px 10px rgba(15,23,42,.08)}
    .form-group{margin-bottom:14px}
    .error{background:#fff1f2;color:#be123c;border:1px solid rgba(190,18,60,.16);padding:12px 14px;border-radius:12px;margin:8px 0 14px}
    .submit-btn{width:100%;border:none;border-radius:14px;padding:13px 16px;background:#0f172a;color:#fff;font-weight:800;cursor:pointer}
    .submit-btn:disabled{opacity:.7;cursor:not-allowed}
    .helper{font-size:.84rem;line-height:1.5;margin-top:14px}
  `]
})
export class AuthComponent {
  mode: AuthMode = 'login';
  email = '';
  password = '';
  confirmPassword = '';
  loading = false;
  error = '';
  registerForm = {
    fullName: ''
  };

  constructor(private auth: AuthService, private router: Router) {
    if (this.auth.isAuthenticated()) {
      this.router.navigate([this.auth.isInternal() ? '/internal/dashboard' : '/dashboard']);
    }
  }

  submit() {
    this.error = '';
    if (!this.email || !this.password) {
      this.error = 'Email and password are required.';
      return;
    }
    if (this.mode === 'register') {
      if (!this.registerForm.fullName.trim()) {
        this.error = 'Full name is required.';
        return;
      }
      if (this.password.length < 8) {
        this.error = 'Password must be at least 8 characters.';
        return;
      }
      if (this.password !== this.confirmPassword) {
        this.error = 'Passwords do not match.';
        return;
      }
    }

    this.loading = true;
    const request = this.mode === 'login'
      ? this.auth.login({ email: this.email, password: this.password })
      : this.auth.register({ fullName: this.registerForm.fullName, email: this.email, password: this.password });

    request.subscribe({
      next: response => {
        this.auth.persistSession(response);
        this.loading = false;
        this.router.navigate([response.user.role === 'INTERNAL' ? '/internal/dashboard' : '/dashboard']);
      },
      error: err => {
        this.loading = false;
        this.error = err?.error?.error || 'Authentication failed.';
      }
    });
  }
}
