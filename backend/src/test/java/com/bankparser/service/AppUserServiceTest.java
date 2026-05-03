package com.bankparser.service;

import com.bankparser.dto.auth.RegisterRequest;
import com.bankparser.model.AppUser;
import com.bankparser.model.UserRole;
import com.bankparser.repository.AppUserRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class AppUserServiceTest {

    @Mock
    AppUserRepository repository;

    @Mock
    PasswordEncoder passwordEncoder;

    AppUserService service;

    @BeforeEach
    void setUp() {
        service = new AppUserService(repository, passwordEncoder, true);
    }

    @Test
    void registerUserNormalizesInputAndHashesPassword() {
        RegisterRequest request = new RegisterRequest();
        request.setFullName("  Asha Rao  ");
        request.setEmail("  ASHA@EXAMPLE.COM ");
        request.setPassword("password123");

        when(repository.existsByEmailIgnoreCase("asha@example.com")).thenReturn(false);
        when(passwordEncoder.encode("password123")).thenReturn("hashed");
        when(repository.save(any(AppUser.class))).thenAnswer(invocation -> invocation.getArgument(0));

        AppUser user = service.registerUser(request);

        assertThat(user.getEmail()).isEqualTo("asha@example.com");
        assertThat(user.getFullName()).isEqualTo("Asha Rao");
        assertThat(user.getPasswordHash()).isEqualTo("hashed");
        assertThat(user.getRole()).isEqualTo(UserRole.USER);
        assertThat(user.isActive()).isTrue();
    }

    @Test
    void registerUserRejectsDuplicateEmail() {
        RegisterRequest request = new RegisterRequest();
        request.setFullName("Asha Rao");
        request.setEmail("asha@example.com");
        request.setPassword("password123");

        when(repository.existsByEmailIgnoreCase("asha@example.com")).thenReturn(true);

        assertThatThrownBy(() -> service.registerUser(request))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("already exists");
    }

    @Test
    void resetPasswordRequiresMatchingFullName() {
        AppUser existing = new AppUser();
        existing.setEmail("asha@example.com");
        existing.setFullName("Asha Rao");
        existing.setPasswordHash("old");

        when(repository.findByEmailIgnoreCase("asha@example.com")).thenReturn(Optional.of(existing));

        assertThatThrownBy(() -> service.resetPassword("asha@example.com", "Someone Else", "newpass123"))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Invalid account recovery details");
    }

    @Test
    void resetPasswordSavesNewHashAndReactivatesUser() {
        AppUser existing = new AppUser();
        existing.setEmail("asha@example.com");
        existing.setFullName("Asha Rao");
        existing.setPasswordHash("old");
        existing.setActive(false);

        when(repository.findByEmailIgnoreCase("asha@example.com")).thenReturn(Optional.of(existing));
        when(passwordEncoder.encode("newpass123")).thenReturn("new-hash");

        service.resetPassword(" ASHA@example.com ", " asha rao ", "newpass123");

        assertThat(existing.getPasswordHash()).isEqualTo("new-hash");
        assertThat(existing.isActive()).isTrue();
        verify(repository).save(existing);
    }
}
