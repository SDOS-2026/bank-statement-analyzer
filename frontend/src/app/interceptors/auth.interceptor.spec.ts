import { TestBed } from '@angular/core/testing';
import { HttpRequest, HttpResponse } from '@angular/common/http';
import { of } from 'rxjs';

import { authInterceptor } from './auth.interceptor';
import { AuthService } from '../services/auth.service';

describe('authInterceptor', () => {
  let auth: jasmine.SpyObj<AuthService>;

  beforeEach(() => {
    auth = jasmine.createSpyObj<AuthService>('AuthService', ['getToken']);
    TestBed.configureTestingModule({
      providers: [{ provide: AuthService, useValue: auth }],
    });
  });

  it('adds bearer tokens when available', () => {
    auth.getToken.and.returnValue('jwt-token');
    const next = jasmine.createSpy('next').and.returnValue(of(new HttpResponse()));
    const request = new HttpRequest('GET', '/api/statements');

    TestBed.runInInjectionContext(() => authInterceptor(request, next));

    const forwarded = next.calls.mostRecent().args[0] as HttpRequest<unknown>;
    expect(forwarded.headers.get('Authorization')).toBe('Bearer jwt-token');
  });

  it('leaves anonymous requests unchanged', () => {
    auth.getToken.and.returnValue(null);
    const next = jasmine.createSpy('next').and.returnValue(of(new HttpResponse()));
    const request = new HttpRequest('GET', '/api/health');

    TestBed.runInInjectionContext(() => authInterceptor(request, next));

    expect(next).toHaveBeenCalledWith(request);
  });
});
