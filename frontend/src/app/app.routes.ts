import { Routes } from '@angular/router';
export const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  { path: 'dashboard', loadComponent: () => import('./components/dashboard/dashboard.component').then(m => m.DashboardComponent) },
  { path: 'upload', loadComponent: () => import('./components/upload/upload.component').then(m => m.UploadComponent) },
  { path: 'statements/:id', loadComponent: () => import('./components/statement-detail/statement-detail.component').then(m => m.StatementDetailComponent) }
];
