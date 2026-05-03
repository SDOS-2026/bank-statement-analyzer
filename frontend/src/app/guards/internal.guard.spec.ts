import { TestBed } from '@angular/core/testing';
import { Router, UrlTree } from '@angular/router';

import { internalGuard } from './internal.guard';
import { AuthService } from '../services/auth.service';

describe('internalGuard', () => {
  let auth: jasmine.SpyObj<AuthService>;
  let router: jasmine.SpyObj<Router>;

  beforeEach(() => {
    auth = jasmine.createSpyObj<AuthService>('AuthService', ['isAuthenticated', 'isInternal']);
    router = jasmine.createSpyObj<Router>('Router', ['createUrlTree']);
    router.createUrlTree.and.returnValue({} as UrlTree);

    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useValue: auth },
        { provide: Router, useValue: router },
      ],
    });
  });

  it('allows internal users', () => {
    auth.isAuthenticated.and.returnValue(true);
    auth.isInternal.and.returnValue(true);

    const result = TestBed.runInInjectionContext(() => internalGuard({} as never, {} as never));

    expect(result).toBeTrue();
  });

  it('redirects unauthenticated users to login', () => {
    auth.isAuthenticated.and.returnValue(false);

    TestBed.runInInjectionContext(() => internalGuard({} as never, {} as never));

    expect(router.createUrlTree).toHaveBeenCalledWith(['/login']);
  });

  it('redirects non-internal users to their dashboard', () => {
    auth.isAuthenticated.and.returnValue(true);
    auth.isInternal.and.returnValue(false);

    TestBed.runInInjectionContext(() => internalGuard({} as never, {} as never));

    expect(router.createUrlTree).toHaveBeenCalledWith(['/dashboard']);
  });
});
