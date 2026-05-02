package com.bankparser.controller;

import com.bankparser.dto.auth.AuthResponse;
import com.bankparser.dto.auth.ForgotPasswordRequest;
import com.bankparser.dto.auth.LoginRequest;
import com.bankparser.dto.auth.RegisterRequest;
import com.bankparser.dto.auth.UserSummaryResponse;
import com.bankparser.model.AppUser;
import com.bankparser.security.AppUserPrincipal;
import com.bankparser.security.JwtService;
import com.bankparser.service.AppUserService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthenticationManager authenticationManager;
    private final AppUserService appUserService;
    private final JwtService jwtService;

    public AuthController(AuthenticationManager authenticationManager,
                          AppUserService appUserService,
                          JwtService jwtService) {
        this.authenticationManager = authenticationManager;
        this.appUserService = appUserService;
        this.jwtService = jwtService;
    }

    @PostMapping("/register")
    public ResponseEntity<?> register(@RequestBody RegisterRequest request) {
        try {
            AppUser user = appUserService.registerUser(request);
            AppUserPrincipal principal = new AppUserPrincipal(user);
            return ResponseEntity.status(HttpStatus.CREATED)
                    .body(new AuthResponse(jwtService.generateToken(principal), UserSummaryResponse.from(user)));
        } catch (IllegalArgumentException ex) {
            return ResponseEntity.badRequest().body(Map.of("error", ex.getMessage()));
        }
    }

    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody LoginRequest request) {
        try {
            Authentication authentication = authenticationManager.authenticate(
                    new UsernamePasswordAuthenticationToken(request.getEmail(), request.getPassword()));
            AppUserPrincipal principal = (AppUserPrincipal) authentication.getPrincipal();
            return ResponseEntity.ok(new AuthResponse(
                    jwtService.generateToken(principal),
                    toUserSummary(principal)
            ));
        } catch (Exception ex) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                    .body(Map.of("error", "Invalid email or password."));
        }
    }

    @PostMapping("/forgot-password")
    public ResponseEntity<?> forgotPassword(@RequestBody ForgotPasswordRequest request) {
        try {
            appUserService.resetPassword(request.getEmail(), request.getFullName(), request.getNewPassword());
            return ResponseEntity.ok(Map.of("message", "Password updated successfully."));
        } catch (IllegalArgumentException ex) {
            return ResponseEntity.badRequest().body(Map.of("error", ex.getMessage()));
        }
    }

    @GetMapping("/me")
    public ResponseEntity<UserSummaryResponse> me() {
        return ResponseEntity.ok(UserSummaryResponse.from(appUserService.getCurrentUser()));
    }

    private UserSummaryResponse toUserSummary(AppUserPrincipal principal) {
        AppUser user = new AppUser();
        user.setId(principal.getId());
        user.setEmail(principal.getEmail());
        user.setFullName(principal.getFullName());
        user.setRole(com.bankparser.model.UserRole.valueOf(principal.getRole()));
        return UserSummaryResponse.from(user);
    }
}
