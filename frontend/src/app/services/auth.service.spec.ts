import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';

import { environment } from '../../environments/environment';
import { AuthService } from './auth.service';
import { AuthResponse } from '../models/auth.model';

describe('AuthService', () => {
  let service: AuthService;
  let http: HttpTestingController;
  const base = `${(environment.apiUrl || '').replace(/\/+$/, '')}/api/auth`;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
    });
    service = TestBed.inject(AuthService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
    localStorage.clear();
  });

  it('persists and clears authenticated sessions', () => {
    const response: AuthResponse = {
      token: 'jwt-token',
      user: { id: 1, email: 'asha@example.com', fullName: 'Asha Rao', role: 'USER' },
    };

    service.persistSession(response);

    expect(service.getToken()).toBe('jwt-token');
    expect(service.currentUser()).toEqual(response.user);
    expect(service.isAuthenticated()).toBeTrue();

    service.logout();

    expect(service.getToken()).toBeNull();
    expect(service.currentUser()).toBeNull();
  });

  it('restores the current user when a stored token is valid', async () => {
    localStorage.setItem('finparse.auth.token', 'jwt-token');

    const restore = service.restoreSession();
    const req = http.expectOne(`${base}/me`);
    expect(req.request.method).toBe('GET');
    req.flush({ id: 2, email: 'internal@example.com', fullName: 'Internal User', role: 'INTERNAL' });
    await restore;

    expect(service.currentUser()?.email).toBe('internal@example.com');
    expect(service.isInternal()).toBeTrue();
  });

  it('logs out when session restoration fails', async () => {
    localStorage.setItem('finparse.auth.token', 'expired-token');

    const restore = service.restoreSession();
    http.expectOne(`${base}/me`).flush({ error: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });
    await restore;

    expect(service.getToken()).toBeNull();
    expect(service.currentUser()).toBeNull();
  });

  it('posts login, registration, and recovery requests to auth endpoints', () => {
    service.login({ email: 'a@example.com', password: 'password123' }).subscribe();
    let req = http.expectOne(`${base}/login`);
    expect(req.request.method).toBe('POST');
    req.flush({ token: 't', user: { id: 1, email: 'a@example.com', fullName: 'A', role: 'USER' } });

    service.register({ fullName: 'A', email: 'a@example.com', password: 'password123' }).subscribe();
    req = http.expectOne(`${base}/register`);
    expect(req.request.method).toBe('POST');
    req.flush({ token: 't', user: { id: 1, email: 'a@example.com', fullName: 'A', role: 'USER' } });

    service.forgotPassword({ email: 'a@example.com', fullName: 'A', newPassword: 'newpass123' }).subscribe();
    req = http.expectOne(`${base}/forgot-password`);
    expect(req.request.method).toBe('POST');
    req.flush({ message: 'Password updated successfully.' });
  });
});
