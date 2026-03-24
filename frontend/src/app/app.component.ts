import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="shell">
      <aside class="sidebar">
        <div class="sidebar-logo">
          <div class="logo-mark">⬡</div>
          <div class="logo-text">
            <span class="logo-name">FinParse</span>
            <span class="logo-tagline">Statement Analyser</span>
          </div>
        </div>
        <nav class="sidebar-nav">
          <a routerLink="/dashboard" routerLinkActive="active" class="nav-item">
            <span class="nav-icon">▦</span><span>Dashboard</span>
          </a>
          <a routerLink="/upload" routerLinkActive="active" class="nav-item">
            <span class="nav-icon">↑</span><span>New Statement</span>
          </a>
        </nav>
        <div class="sidebar-footer">
          <div class="text-sm text-muted">FinParse v1.0</div>
        </div>
      </aside>
      <main class="content"><router-outlet /></main>
    </div>
  `,
  styles: [` 
    .shell{display:flex;height:100vh;overflow:hidden}
    .sidebar{width:220px;min-width:220px;background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;padding:24px 16px}
    .sidebar-logo{display:flex;align-items:center;gap:12px;margin-bottom:40px;padding:0 8px}
    .logo-mark{font-size:1.8rem;color:var(--accent);line-height:1}
    .logo-name{display:block;font-family:'DM Serif Display',serif;font-size:1.1rem;color:var(--text-1);line-height:1.2}
    .logo-tagline{display:block;font-size:0.68rem;color:var(--text-3);text-transform:uppercase;letter-spacing:0.08em}
    .sidebar-nav{display:flex;flex-direction:column;gap:4px;flex:1}
    .nav-item{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:var(--radius-sm);color:var(--text-2);text-decoration:none;font-size:0.88rem;transition:var(--transition)}
    .nav-item:hover{background:var(--surface-2);color:var(--text-1)}
    .nav-item.active{background:var(--accent-dim);color:var(--accent)}
    .nav-icon{font-size:1rem;width:20px;text-align:center}
    .sidebar-footer{border-top:1px solid var(--border);padding-top:16px}
    .content{flex:1;overflow-y:auto}
  `]
})
export class AppComponent {}
