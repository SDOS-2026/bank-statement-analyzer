import { Routes } from '@angular/router';
import { authGuard } from './guards/auth.guard';
import { internalGuard } from './guards/internal.guard';

export const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  { path: 'login', loadComponent: () => import('./components/auth/auth.component').then(m => m.AuthComponent) },
  {
    path: 'dashboard',
    canActivate: [authGuard],
    data: { scope: 'mine' },
    loadComponent: () => import('./components/dashboard/dashboard.component').then(m => m.DashboardComponent)
  },
  {
    path: 'internal/dashboard',
    canActivate: [internalGuard],
    data: { scope: 'all' },
    loadComponent: () => import('./components/dashboard/dashboard.component').then(m => m.DashboardComponent)
  },
  { path: 'upload', canActivate: [authGuard], loadComponent: () => import('./components/upload/upload.component').then(m => m.UploadComponent) },
  { path: 'statements/:id', canActivate: [authGuard], loadComponent: () => import('./components/statement-detail/statement-detail.component').then(m => m.StatementDetailComponent) }
];
