package com.bankparser.service;

import com.bankparser.dto.auth.RegisterRequest;
import com.bankparser.model.AppUser;
import com.bankparser.model.UserRole;
import com.bankparser.repository.AppUserRepository;
import com.bankparser.security.AppUserPrincipal;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

@Service
public class AppUserService implements UserDetailsService {

    private final AppUserRepository appUserRepository;
    private final PasswordEncoder passwordEncoder;
    private final boolean allowPublicRegistration;

    public AppUserService(AppUserRepository appUserRepository,
                          PasswordEncoder passwordEncoder,
                          @Value("${app.auth.allow-public-registration:true}") boolean allowPublicRegistration) {
        this.appUserRepository = appUserRepository;
        this.passwordEncoder = passwordEncoder;
        this.allowPublicRegistration = allowPublicRegistration;
    }

    public AppUser registerUser(RegisterRequest request) {
        if (!allowPublicRegistration) {
            throw new IllegalArgumentException("Public registration is disabled.");
        }
        String email = normalizeEmail(request.getEmail());
        if (email == null) {
            throw new IllegalArgumentException("Email is required.");
        }
        if (!StringUtils.hasText(request.getFullName())) {
            throw new IllegalArgumentException("Full name is required.");
        }
        if (!StringUtils.hasText(request.getPassword()) || request.getPassword().length() < 8) {
            throw new IllegalArgumentException("Password must be at least 8 characters.");
        }
        if (appUserRepository.existsByEmailIgnoreCase(email)) {
            throw new IllegalArgumentException("An account with this email already exists.");
        }

        AppUser user = new AppUser();
        user.setEmail(email);
        user.setFullName(request.getFullName().trim());
        user.setPasswordHash(passwordEncoder.encode(request.getPassword()));
        user.setRole(UserRole.USER);
        user.setActive(true);
        return appUserRepository.save(user);
    }

    public void resetPassword(String email, String fullName, String newPassword) {
        String normalizedEmail = normalizeEmail(email);
        if (normalizedEmail == null) {
            throw new IllegalArgumentException("Email is required.");
        }
        if (!StringUtils.hasText(fullName)) {
            throw new IllegalArgumentException("Full name is required.");
        }
        if (!StringUtils.hasText(newPassword) || newPassword.length() < 8) {
            throw new IllegalArgumentException("Password must be at least 8 characters.");
        }

        AppUser user = appUserRepository.findByEmailIgnoreCase(normalizedEmail)
                .orElseThrow(() -> new IllegalArgumentException("Invalid account recovery details."));

        if (!user.getFullName().trim().equalsIgnoreCase(fullName.trim())) {
            throw new IllegalArgumentException("Invalid account recovery details.");
        }

        user.setPasswordHash(passwordEncoder.encode(newPassword));
        user.setActive(true);
        appUserRepository.save(user);
    }

    public AppUser getCurrentUser() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || !(authentication.getPrincipal() instanceof AppUserPrincipal principal)) {
            throw new IllegalStateException("No authenticated user is available.");
        }
        return appUserRepository.findById(principal.getId())
                .orElseThrow(() -> new UsernameNotFoundException("User not found."));
    }

    public AppUser bootstrapInternalUser(String email, String password, String fullName) {
        if (!StringUtils.hasText(email) || !StringUtils.hasText(password)) {
            return null;
        }
        String normalizedEmail = normalizeEmail(email);
        return appUserRepository.findByEmailIgnoreCase(normalizedEmail)
                .map(existing -> {
                    if (existing.getRole() != UserRole.INTERNAL) {
                        existing.setRole(UserRole.INTERNAL);
                    }
                    existing.setFullName(StringUtils.hasText(fullName) ? fullName.trim() : existing.getFullName());
                    existing.setPasswordHash(passwordEncoder.encode(password));
                    existing.setActive(true);
                    return appUserRepository.save(existing);
                })
                .orElseGet(() -> {
                    AppUser user = new AppUser();
                    user.setEmail(normalizedEmail);
                    user.setFullName(StringUtils.hasText(fullName) ? fullName.trim() : "FinParse Internal Admin");
                    user.setPasswordHash(passwordEncoder.encode(password));
                    user.setRole(UserRole.INTERNAL);
                    user.setActive(true);
                    return appUserRepository.save(user);
                });
    }

    @Override
    public UserDetails loadUserByUsername(String username) throws UsernameNotFoundException {
        AppUser user = appUserRepository.findByEmailIgnoreCase(normalizeEmail(username))
                .orElseThrow(() -> new UsernameNotFoundException("User not found."));
        return new AppUserPrincipal(user);
    }

    private String normalizeEmail(String email) {
        return StringUtils.hasText(email) ? email.trim().toLowerCase() : null;
    }
}
