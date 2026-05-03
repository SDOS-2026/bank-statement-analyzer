package com.bankparser.controller;

import com.bankparser.dto.auth.AuthResponse;
import com.bankparser.dto.auth.ForgotPasswordRequest;
import com.bankparser.dto.auth.LoginRequest;
import com.bankparser.dto.auth.RegisterRequest;
import com.bankparser.dto.auth.UserSummaryResponse;
import com.bankparser.model.AppUser;
import com.bankparser.model.UserRole;
import com.bankparser.security.AppUserPrincipal;
import com.bankparser.security.JwtService;
import com.bankparser.service.AppUserService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Integration tests for AuthController.
 * Tests user registration, login, password recovery, and session endpoints.
 */
@ExtendWith(MockitoExtension.class)
class AuthControllerIntegrationTest {

    @Mock
    AuthenticationManager authenticationManager;

    @Mock
    AppUserService appUserService;

    @Mock
    JwtService jwtService;

    AuthController controller;
    ObjectMapper objectMapper;

    @BeforeEach
    void setUp() {
        controller = new AuthController(authenticationManager, appUserService, jwtService);
        objectMapper = new ObjectMapper();
    }

    private AppUser user(long id, String email, String fullName, UserRole role) {
        AppUser u = new AppUser();
        u.setId(id);
        u.setEmail(email);
        u.setFullName(fullName);
        u.setRole(role);
        u.setPasswordHash("hashed");
        u.setActive(true);
        return u;
    }

    // ==================== Registration Tests ====================

    @Test
    void registerUserSucceedsAndReturns201() {
        RegisterRequest request = new RegisterRequest();
        request.setEmail("newuser@example.com");
        request.setFullName("New User");
        request.setPassword("SecurePass123");

        AppUser registeredUser = user(1L, "newuser@example.com", "New User", UserRole.USER);
        when(appUserService.registerUser(request)).thenReturn(registeredUser);
        when(jwtService.generateToken(any(AppUserPrincipal.class))).thenReturn("jwt_token_123");

        ResponseEntity<?> response = controller.register(request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        assertThat(response.getBody()).isInstanceOf(AuthResponse.class);

        AuthResponse authResponse = (AuthResponse) response.getBody();
        assertThat(authResponse.token()).isEqualTo("jwt_token_123");
        assertThat(authResponse.user().email()).isEqualTo("newuser@example.com");
        assertThat(authResponse.user().fullName()).isEqualTo("New User");
        assertThat(authResponse.user().role()).isEqualTo("USER");

        verify(appUserService).registerUser(request);
        verify(jwtService).generateToken(any(AppUserPrincipal.class));
    }

    @Test
    void registerUserFailsWithBadRequest() {
        RegisterRequest request = new RegisterRequest();
        request.setEmail("invalid");
        request.setFullName("");
        request.setPassword("short");

        when(appUserService.registerUser(request))
                .thenThrow(new IllegalArgumentException("Full name is required."));

        ResponseEntity<?> response = controller.register(request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(response.getBody()).isInstanceOf(Map.class);

        @SuppressWarnings("unchecked")
        Map<String, String> body = (Map<String, String>) response.getBody();
        assertThat(body.get("error")).contains("Full name");
    }

    @Test
    void registerUserReturnsErrorWhenEmailAlreadyExists() {
        RegisterRequest request = new RegisterRequest();
        request.setEmail("existing@example.com");
        request.setFullName("User");
        request.setPassword("Password123");

        when(appUserService.registerUser(request))
                .thenThrow(new IllegalArgumentException("An account with this email already exists."));

        ResponseEntity<?> response = controller.register(request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);

        @SuppressWarnings("unchecked")
        Map<String, String> body = (Map<String, String>) response.getBody();
        assertThat(body.get("error")).contains("already exists");
    }

    // ==================== Login Tests ====================

    @Test
    void loginSucceedsWithValidCredentials() {
        LoginRequest request = new LoginRequest();
        request.setEmail("user@example.com");
        request.setPassword("Password123");

        AppUser loginUser = user(1L, "user@example.com", "User Name", UserRole.USER);
        AppUserPrincipal principal = new AppUserPrincipal(loginUser);

        Authentication auth = new UsernamePasswordAuthenticationToken(principal, null, principal.getAuthorities());
        when(authenticationManager.authenticate(any(UsernamePasswordAuthenticationToken.class))).thenReturn(auth);
        when(jwtService.generateToken(principal)).thenReturn("jwt_token_abc");

        ResponseEntity<?> response = controller.login(request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).isInstanceOf(AuthResponse.class);

        AuthResponse authResponse = (AuthResponse) response.getBody();
        assertThat(authResponse.token()).isEqualTo("jwt_token_abc");
        assertThat(authResponse.user().email()).isEqualTo("user@example.com");

        verify(authenticationManager).authenticate(any(UsernamePasswordAuthenticationToken.class));
        verify(jwtService).generateToken(principal);
    }

    @Test
    void loginFailsWithInvalidPassword() {
        LoginRequest request = new LoginRequest();
        request.setEmail("user@example.com");
        request.setPassword("WrongPassword");

        when(authenticationManager.authenticate(any(UsernamePasswordAuthenticationToken.class)))
                .thenThrow(new BadCredentialsException("Invalid credentials"));

        ResponseEntity<?> response = controller.login(request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.UNAUTHORIZED);

        @SuppressWarnings("unchecked")
        Map<String, String> body = (Map<String, String>) response.getBody();
        assertThat(body.get("error")).contains("Invalid email or password");
    }

    @Test
    void loginFailsWithNonExistentUser() {
        LoginRequest request = new LoginRequest();
        request.setEmail("nonexistent@example.com");
        request.setPassword("Password123");

        when(authenticationManager.authenticate(any(UsernamePasswordAuthenticationToken.class)))
                .thenThrow(new BadCredentialsException("Invalid credentials"));

        ResponseEntity<?> response = controller.login(request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.UNAUTHORIZED);
    }

    // ==================== Forgot Password Tests ====================

    @Test
    void forgotPasswordSucceedsWithValidDetails() {
        ForgotPasswordRequest request = new ForgotPasswordRequest();
        request.setEmail("user@example.com");
        request.setFullName("User Name");
        request.setNewPassword("NewPassword123");

        ResponseEntity<?> response = controller.forgotPassword(request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);

        @SuppressWarnings("unchecked")
        Map<String, String> body = (Map<String, String>) response.getBody();
        assertThat(body.get("message")).contains("Password updated successfully");

        verify(appUserService).resetPassword("user@example.com", "User Name", "NewPassword123");
    }

    @Test
    void forgotPasswordFailsWithWrongFullName() {
        ForgotPasswordRequest request = new ForgotPasswordRequest();
        request.setEmail("user@example.com");
        request.setFullName("Wrong Name");
        request.setNewPassword("NewPassword123");

        when(appUserService.resetPassword(request.getEmail(), request.getFullName(), request.getNewPassword()))
                .thenThrow(new IllegalArgumentException("Invalid account recovery details."));

        ResponseEntity<?> response = controller.forgotPassword(request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);

        @SuppressWarnings("unchecked")
        Map<String, String> body = (Map<String, String>) response.getBody();
        assertThat(body.get("error")).contains("Invalid");
    }

    @Test
    void forgotPasswordFailsWithNonExistentUser() {
        ForgotPasswordRequest request = new ForgotPasswordRequest();
        request.setEmail("nonexistent@example.com");
        request.setFullName("Some Name");
        request.setNewPassword("NewPassword123");

        when(appUserService.resetPassword(request.getEmail(), request.getFullName(), request.getNewPassword()))
                .thenThrow(new IllegalArgumentException("Invalid account recovery details."));

        ResponseEntity<?> response = controller.forgotPassword(request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
    }

    @Test
    void forgotPasswordFailsWithWeakPassword() {
        ForgotPasswordRequest request = new ForgotPasswordRequest();
        request.setEmail("user@example.com");
        request.setFullName("User Name");
        request.setNewPassword("weak");

        when(appUserService.resetPassword(request.getEmail(), request.getFullName(), request.getNewPassword()))
                .thenThrow(new IllegalArgumentException("Password must be at least 8 characters."));

        ResponseEntity<?> response = controller.forgotPassword(request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);

        @SuppressWarnings("unchecked")
        Map<String, String> body = (Map<String, String>) response.getBody();
        assertThat(body.get("error")).contains("at least 8 characters");
    }

    // ==================== Session (Me) Tests ====================

    @Test
    void meReturnsCurrentUserDetails() {
        AppUser currentUser = user(1L, "user@example.com", "User Name", UserRole.USER);
        when(appUserService.getCurrentUser()).thenReturn(currentUser);

        ResponseEntity<UserSummaryResponse> response = controller.me();

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().email()).isEqualTo("user@example.com");
        assertThat(response.getBody().fullName()).isEqualTo("User Name");
        assertThat(response.getBody().role()).isEqualTo("USER");

        verify(appUserService).getCurrentUser();
    }

    @Test
    void meReturnsInternalUserRole() {
        AppUser currentUser = user(2L, "admin@example.com", "Admin User", UserRole.INTERNAL);
        when(appUserService.getCurrentUser()).thenReturn(currentUser);

        ResponseEntity<UserSummaryResponse> response = controller.me();

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody().role()).isEqualTo("INTERNAL");
    }
}
