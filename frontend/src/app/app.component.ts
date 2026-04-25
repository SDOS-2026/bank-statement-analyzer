import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { AuthService } from './services/auth.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <router-outlet *ngIf="isAuthPage(); else appShell" />
    <ng-template #appShell>
      <div class="shell">
        <aside class="sidebar">
          <div class="sidebar-logo">
            <div class="logo-mark">FP</div>
            <div class="logo-text">
              <span class="logo-name">FinParse</span>
              <span class="logo-tagline">Statement Analyser</span>
            </div>
          </div>
          <nav class="sidebar-nav">
            <a routerLink="/dashboard" routerLinkActive="active" class="nav-item">
              <span class="nav-icon">01</span><span>My Statements</span>
            </a>
            <a *ngIf="auth.isInternal()" routerLink="/internal/dashboard" routerLinkActive="active" class="nav-item">
              <span class="nav-icon">02</span><span>Internal</span>
            </a>
            <a routerLink="/upload" routerLinkActive="active" class="nav-item">
              <span class="nav-icon">03</span><span>New Statement</span>
            </a>
          </nav>
          <div class="sidebar-footer">
            <div>
              <div class="footer-title">{{ auth.currentUser()?.fullName || 'Signed in' }}</div>
              <div class="text-sm text-muted">{{ auth.currentUser()?.email }}</div>
              <div class="text-sm text-muted">{{ auth.isInternal() ? 'Internal reviewer' : 'Customer workspace' }}</div>
            </div>
            <button class="logout-btn" (click)="logout()">Logout</button>
          </div>
        </aside>
        <main class="content">
          <div class="mobile-bar">
            <div class="logo-mark">FP</div>
            <div>
              <span class="logo-name">FinParse</span>
              <span class="logo-tagline">Statement Analyser</span>
            </div>
            <button class="logout-btn mobile-logout" (click)="logout()">Logout</button>
          </div>
          <router-outlet />
        </main>
      </div>
    </ng-template>
  `,
  styles: [`
    .shell{display:flex;height:100vh;overflow:hidden;background:var(--bg)}
    .sidebar{width:248px;min-width:248px;background:#fff;border-right:1px solid var(--border);display:flex;flex-direction:column;padding:22px 16px}
    .sidebar-logo{display:flex;align-items:center;gap:10px;margin-bottom:34px;padding:6px 8px}
    .logo-mark{width:38px;height:38px;border-radius:8px;background:var(--text-1);color:#fff;display:inline-flex;align-items:center;justify-content:center;font-weight:800;font-size:.82rem}
    .logo-name{display:block;font-size:1.08rem;font-weight:800;color:var(--text-1);line-height:1.2}
    .logo-tagline{display:block;font-size:0.68rem;color:var(--text-3);text-transform:uppercase;letter-spacing:0.08em}
    .sidebar-nav{display:flex;flex-direction:column;gap:6px;flex:1}
    .nav-item{display:flex;align-items:center;gap:11px;padding:11px 12px;border-radius:var(--radius);color:var(--text-2);text-decoration:none;font-size:0.9rem;font-weight:650;transition:var(--transition)}
    .nav-item:hover{background:var(--surface-2);color:var(--text-1);border-color:var(--border)}
    .nav-item.active{background:var(--text-1);color:#fff}
    .nav-icon{font-size:.68rem;width:24px;height:24px;border-radius:6px;background:var(--surface-2);color:var(--text-2);display:inline-flex;align-items:center;justify-content:center;font-weight:800}
    .nav-item.active .nav-icon{background:rgba(255,255,255,.14);color:#fff}
    .sidebar-footer{border-top:1px solid var(--border);padding:16px 8px 4px;display:flex;align-items:flex-start;gap:10px}
    .footer-title{font-size:.78rem;font-weight:750;color:var(--text-1)}
    .logout-btn{margin-left:auto;border:none;background:var(--surface-2);border-radius:10px;padding:8px 12px;font-size:.78rem;font-weight:700;color:var(--text-2);cursor:pointer}
    .logout-btn:hover{background:var(--surface-3);color:var(--text-1)}
    .content{flex:1;overflow-y:auto;min-width:0;background:var(--bg)}
    .mobile-bar{display:none}
    .mobile-logout{margin-left:auto}
    @media (max-width: 820px){
      .shell{display:block;overflow:auto}
      .sidebar{display:none}
      .content{min-height:100vh;overflow:visible}
      .mobile-bar{display:flex;align-items:center;gap:12px;padding:14px 20px;background:#fff;border-bottom:1px solid var(--border);position:sticky;top:0;z-index:5}
    }
  `]
})
export class AppComponent {
  constructor(public auth: AuthService, private router: Router) {}

  isAuthPage() {
    return this.router.url.startsWith('/login');
  }

  logout() {
    this.auth.logout();
    this.router.navigate(['/login']);
  }
}
