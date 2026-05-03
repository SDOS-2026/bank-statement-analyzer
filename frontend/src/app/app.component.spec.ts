import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { AppComponent } from './app.component';
import { AuthService } from './services/auth.service';

describe('AppComponent', () => {
  beforeEach(async () => {
    const auth = jasmine.createSpyObj<AuthService>('AuthService', ['currentUser', 'isInternal', 'logout']);
    auth.currentUser.and.returnValue({
      id: 1,
      fullName: 'Test User',
      email: 'test@example.com',
      role: 'USER',
    });
    auth.isInternal.and.returnValue(false);

    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: auth },
      ],
    }).compileComponents();
  });

  it('creates the application shell', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it('renders the product brand in the sidebar', () => {
    const fixture = TestBed.createComponent(AppComponent);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('.logo-name')?.textContent).toContain('FinParse');
    expect(compiled.querySelector('.logo-tagline')?.textContent).toContain('Statement Analyser');
  });

  it('exposes the primary navigation links', () => {
    const fixture = TestBed.createComponent(AppComponent);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const links = Array.from(compiled.querySelectorAll('.nav-item')).map((a) => a.textContent?.trim());

    expect(links.some((text) => text?.includes('My Statements'))).toBeTrue();
    expect(links.some((text) => text?.includes('New Statement'))).toBeTrue();
  });
});
