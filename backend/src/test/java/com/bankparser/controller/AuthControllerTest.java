package com.bankparser.controller;

import com.bankparser.dto.auth.LoginRequest;
import com.bankparser.dto.auth.RegisterRequest;
import com.bankparser.model.AppUser;
import com.bankparser.model.UserRole;
import com.bankparser.security.AppUserPrincipal;
import com.bankparser.security.JwtService;
import com.bankparser.service.AppUserService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class AuthControllerTest {

    @Mock
    AuthenticationManager authenticationManager;

    @Mock
    AppUserService appUserService;

    @Mock
    JwtService jwtService;

    @Mock
    Authentication authentication;

    AuthController controller;

    @BeforeEach
    void setUp() {
        controller = new AuthController(authenticationManager, appUserService, jwtService);
    }

    @Test
    void registerReturnsCreatedWithToken() {
        AppUser user = user();
        RegisterRequest request = new RegisterRequest();
        request.setEmail("asha@example.com");
        request.setFullName("Asha Rao");
        request.setPassword("password123");

        when(appUserService.registerUser(request)).thenReturn(user);
        when(jwtService.generateToken(any(AppUserPrincipal.class))).thenReturn("jwt-token");

        ResponseEntity<?> response = controller.register(request);

        assertThat(response.getStatusCode().value()).isEqualTo(201);
        assertThat(response.getBody()).hasFieldOrPropertyWithValue("token", "jwt-token");
    }

    @Test
    void registerReturnsBadRequestForValidationErrors() {
        RegisterRequest request = new RegisterRequest();
        when(appUserService.registerUser(request)).thenThrow(new IllegalArgumentException("Email is required."));

        ResponseEntity<?> response = controller.register(request);

        assertThat(response.getStatusCode().value()).isEqualTo(400);
        assertThat(response.getBody()).isEqualTo(Map.of("error", "Email is required."));
    }

    @Test
    void loginReturnsUnauthorizedWhenAuthenticationFails() {
        LoginRequest request = new LoginRequest();
        request.setEmail("asha@example.com");
        request.setPassword("bad");

        when(authenticationManager.authenticate(any(UsernamePasswordAuthenticationToken.class)))
                .thenThrow(new RuntimeException("bad credentials"));

        ResponseEntity<?> response = controller.login(request);

        assertThat(response.getStatusCode().value()).isEqualTo(401);
        assertThat(response.getBody()).isEqualTo(Map.of("error", "Invalid email or password."));
    }

    @Test
    void loginReturnsTokenAndUserSummary() {
        LoginRequest request = new LoginRequest();
        request.setEmail("asha@example.com");
        request.setPassword("password123");

        AppUserPrincipal principal = new AppUserPrincipal(user());
        when(authenticationManager.authenticate(any(UsernamePasswordAuthenticationToken.class)))
                .thenReturn(authentication);
        when(authentication.getPrincipal()).thenReturn(principal);
        when(jwtService.generateToken(principal)).thenReturn("jwt-token");

        ResponseEntity<?> response = controller.login(request);

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(response.getBody()).hasFieldOrPropertyWithValue("token", "jwt-token");
    }

    private AppUser user() {
        AppUser user = new AppUser();
        user.setId(1L);
        user.setEmail("asha@example.com");
        user.setFullName("Asha Rao");
        user.setPasswordHash("hashed");
        user.setRole(UserRole.USER);
        user.setActive(true);
        return user;
    }
}
