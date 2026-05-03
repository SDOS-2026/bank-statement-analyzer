package com.bankparser.integration;

import com.bankparser.dto.auth.LoginRequest;
import com.bankparser.dto.auth.RegisterRequest;
import com.bankparser.model.AppUser;
import com.bankparser.model.Statement;
import com.bankparser.model.Transaction;
import com.bankparser.model.UserRole;
import com.bankparser.repository.AppUserRepository;
import com.bankparser.repository.StatementRepository;
import com.bankparser.repository.TransactionRepository;
import com.bankparser.service.AppUserService;
import com.bankparser.service.StatementService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.client.RestTemplate;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Comprehensive error scenario and edge case tests across all backend services.
 * Tests error handling, boundary conditions, and exception scenarios.
 */
@ExtendWith(MockitoExtension.class)
class BackendErrorScenarioIntegrationTest {

    @Mock
    AppUserRepository appUserRepository;

    @Mock
    StatementRepository statementRepository;

    @Mock
    TransactionRepository transactionRepository;

    @Mock
    PasswordEncoder passwordEncoder;

    @Mock
    RestTemplate restTemplate;

    AppUserService appUserService;
    StatementService statementService;
    ObjectMapper objectMapper;

    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper();
        appUserService = new AppUserService(appUserRepository, passwordEncoder, true);
        statementService = new StatementService(statementRepository, transactionRepository, restTemplate, objectMapper, appUserService);
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

    private Statement statement(Long id, String status) {
        Statement s = new Statement();
        s.setId(id);
        s.setStatus(status);
        s.setCustomerName("Test User");
        return s;
    }

    // ==================== Authentication Error Scenarios ====================

    @Test
    void handleRegistrationWithNullEmail() {
        RegisterRequest request = new RegisterRequest();
        request.setEmail(null);
        request.setFullName("John Doe");
        request.setPassword("SecurePass123");

        assertThatThrownBy(() -> appUserService.registerUser(request))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Email");
    }

    @Test
    void handleRegistrationWithNullFullName() {
        RegisterRequest request = new RegisterRequest();
        request.setEmail("john@example.com");
        request.setFullName(null);
        request.setPassword("SecurePass123");

        assertThatThrownBy(() -> appUserService.registerUser(request))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Full name");
    }

    @Test
    void handleRegistrationWithNullPassword() {
        RegisterRequest request = new RegisterRequest();
        request.setEmail("john@example.com");
        request.setFullName("John Doe");
        request.setPassword(null);

        assertThatThrownBy(() -> appUserService.registerUser(request))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Password");
    }

    @Test
    void handleRegistrationWithWhitespaceOnlyEmail() {
        RegisterRequest request = new RegisterRequest();
        request.setEmail("   ");
        request.setFullName("John Doe");
        request.setPassword("SecurePass123");

        assertThatThrownBy(() -> appUserService.registerUser(request))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void handleRegistrationWithWhitespaceOnlyPassword() {
        RegisterRequest request = new RegisterRequest();
        request.setEmail("john@example.com");
        request.setFullName("John Doe");
        request.setPassword("        ");

        assertThatThrownBy(() -> appUserService.registerUser(request))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Password");
    }

    @Test
    void handleRegistrationWithExtremelyLongEmail() {
        RegisterRequest request = new RegisterRequest();
        request.setEmail("a".repeat(255) + "@example.com");
        request.setFullName("John Doe");
        request.setPassword("SecurePass123");

        when(appUserRepository.existsByEmailIgnoreCase(request.getEmail())).thenReturn(false);
        when(passwordEncoder.encode("SecurePass123")).thenReturn("hashed");
        AppUser savedUser = user(1L, request.getEmail(), "John Doe", UserRole.USER);
        when(appUserRepository.save(any(AppUser.class))).thenReturn(savedUser);

        AppUser result = appUserService.registerUser(request);
        assertThat(result).isNotNull();
    }

    @Test
    void handleRegistrationWithExtremelyLongFullName() {
        RegisterRequest request = new RegisterRequest();
        request.setEmail("john@example.com");
        request.setFullName("A".repeat(500));
        request.setPassword("SecurePass123");

        when(appUserRepository.existsByEmailIgnoreCase("john@example.com")).thenReturn(false);
        when(passwordEncoder.encode("SecurePass123")).thenReturn("hashed");
        AppUser savedUser = user(1L, "john@example.com", request.getFullName(), UserRole.USER);
        when(appUserRepository.save(any(AppUser.class))).thenReturn(savedUser);

        AppUser result = appUserService.registerUser(request);
        assertThat(result.getFullName()).hasLength(500);
    }

    @Test
    void handlePasswordResetWithNullEmail() {
        assertThatThrownBy(() -> appUserService.resetPassword(null, "John Doe", "NewPass123"))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void handlePasswordResetWithNullFullName() {
        assertThatThrownBy(() -> appUserService.resetPassword("john@example.com", null, "NewPass123"))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void handlePasswordResetWithNullNewPassword() {
        assertThatThrownBy(() -> appUserService.resetPassword("john@example.com", "John Doe", null))
                .isInstanceOf(IllegalArgumentException.class);
    }

    // ==================== Statement Error Scenarios ====================

    @Test
    void handleGetStatementWithNegativeId() {
        when(statementRepository.findById(-1L)).thenReturn(Optional.empty());

        Optional<Statement> result = statementService.getStatement(-1L);

        assertThat(result).isEmpty();
    }

    @Test
    void handleGetStatementWithZeroId() {
        when(statementRepository.findById(0L)).thenReturn(Optional.empty());

        Optional<Statement> result = statementService.getStatement(0L);

        assertThat(result).isEmpty();
    }

    @Test
    void handleGetStatementWithVeryLargeId() {
        when(statementRepository.findById(Long.MAX_VALUE)).thenReturn(Optional.empty());

        Optional<Statement> result = statementService.getStatement(Long.MAX_VALUE);

        assertThat(result).isEmpty();
    }

    @Test
    void handleGetTransactionsWithEmptyList() {
        when(transactionRepository.findByStatementIdOrderByDateDesc(1L)).thenReturn(List.of());

        List<Transaction> result = statementService.getTransactions(1L);

        assertThat(result).isEmpty();
    }

    @Test
    void handleGetTransactionsWithNullBalance() {
        Transaction t = new Transaction();
        t.setId(1L);
        t.setDescription("Test");
        t.setBalance(null);

        when(transactionRepository.findByStatementIdOrderByDateDesc(1L)).thenReturn(List.of(t));

        List<Transaction> result = statementService.getTransactions(1L);

        assertThat(result).hasSize(1);
        assertThat(result.get(0).getBalance()).isNull();
    }

    @Test
    void handleGetTransactionsWithZeroAmounts() {
        Transaction t = new Transaction();
        t.setId(1L);
        t.setDescription("Zero amount");
        t.setDebit(0.0);
        t.setCredit(0.0);

        when(transactionRepository.findByStatementIdOrderByDateDesc(1L)).thenReturn(List.of(t));

        List<Transaction> result = statementService.getTransactions(1L);

        assertThat(result).hasSize(1);
        assertThat(result.get(0).getDebit()).isZero();
    }

    @Test
    void handleGetTransactionsWithNegativeAmounts() {
        Transaction t = new Transaction();
        t.setId(1L);
        t.setDescription("Negative amount");
        t.setDebit(-500.0);
        t.setCredit(1000.0);

        when(transactionRepository.findByStatementIdOrderByDateDesc(1L)).thenReturn(List.of(t));

        List<Transaction> result = statementService.getTransactions(1L);

        assertThat(result).hasSize(1);
        assertThat(result.get(0).getDebit()).isNegative();
    }

    @Test
    void handleDeleteNonExistentStatement() {
        AppUser currentUser = user(1L, "user@example.com", "User", UserRole.USER);
        when(appUserService.getCurrentUser()).thenReturn(currentUser);
        when(statementRepository.findById(99L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> statementService.deleteStatement(99L))
                .isInstanceOf(Exception.class);
    }

    @Test
    void handleUnlockWithNullPassword() {
        AppUser currentUser = user(1L, "user@example.com", "User", UserRole.USER);
        Statement stmt = statement(1L, "PENDING");
        when(appUserService.getCurrentUser()).thenReturn(currentUser);
        when(statementRepository.findById(1L)).thenReturn(Optional.of(stmt));

        assertThatThrownBy(() -> statementService.unlockWithPassword(1L, null))
                .isInstanceOf(Exception.class);
    }

    @Test
    void handleUnlockWithEmptyPassword() {
        AppUser currentUser = user(1L, "user@example.com", "User", UserRole.USER);
        Statement stmt = statement(1L, "PENDING");
        when(appUserService.getCurrentUser()).thenReturn(currentUser);
        when(statementRepository.findById(1L)).thenReturn(Optional.of(stmt));

        assertThatThrownBy(() -> statementService.unlockWithPassword(1L, ""))
                .isInstanceOf(Exception.class);
    }

    // ==================== Boundary Condition Tests ====================

    @Test
    void handleRegistrationWithMinimumLengthPassword() {
        RegisterRequest request = new RegisterRequest();
        request.setEmail("john@example.com");
        request.setFullName("John Doe");
        request.setPassword("12345678");  // Exactly 8 characters

        when(appUserRepository.existsByEmailIgnoreCase("john@example.com")).thenReturn(false);
        when(passwordEncoder.encode("12345678")).thenReturn("hashed");
        AppUser savedUser = user(1L, "john@example.com", "John Doe", UserRole.USER);
        when(appUserRepository.save(any(AppUser.class))).thenReturn(savedUser);

        AppUser result = appUserService.registerUser(request);

        assertThat(result).isNotNull();
        verify(appUserRepository).save(any(AppUser.class));
    }

    @Test
    void handleRegistrationWithOneCharacterBelowMinimumPassword() {
        RegisterRequest request = new RegisterRequest();
        request.setEmail("john@example.com");
        request.setFullName("John Doe");
        request.setPassword("1234567");  // Only 7 characters

        assertThatThrownBy(() -> appUserService.registerUser(request))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Password");
    }

    @Test
    void handleRegistrationWithMaximumLengthPassword() {
        RegisterRequest request = new RegisterRequest();
        request.setEmail("john@example.com");
        request.setFullName("John Doe");
        request.setPassword("a".repeat(256));  // Very long password

        when(appUserRepository.existsByEmailIgnoreCase("john@example.com")).thenReturn(false);
        when(passwordEncoder.encode(request.getPassword())).thenReturn("hashed");
        AppUser savedUser = user(1L, "john@example.com", "John Doe", UserRole.USER);
        when(appUserRepository.save(any(AppUser.class))).thenReturn(savedUser);

        AppUser result = appUserService.registerUser(request);
        assertThat(result).isNotNull();
    }

    // ==================== Email Format Tests ====================

    @Test
    void handleRegistrationWithInvalidEmailFormat() {
        RegisterRequest request = new RegisterRequest();
        request.setEmail("notanemail");
        request.setFullName("John Doe");
        request.setPassword("SecurePass123");

        // Email validation might happen elsewhere, but service should handle it
        when(appUserRepository.existsByEmailIgnoreCase("notanemail")).thenReturn(false);
        when(passwordEncoder.encode("SecurePass123")).thenReturn("hashed");
        AppUser savedUser = user(1L, "notanemail", "John Doe", UserRole.USER);
        when(appUserRepository.save(any(AppUser.class))).thenReturn(savedUser);

        AppUser result = appUserService.registerUser(request);
        assertThat(result).isNotNull();
    }

    @Test
    void handleRegistrationWithEmailContainingSpecialCharacters() {
        RegisterRequest request = new RegisterRequest();
        request.setEmail("john+test@example.co.uk");
        request.setFullName("John Doe");
        request.setPassword("SecurePass123");

        when(appUserRepository.existsByEmailIgnoreCase("john+test@example.co.uk")).thenReturn(false);
        when(passwordEncoder.encode("SecurePass123")).thenReturn("hashed");
        AppUser savedUser = user(1L, "john+test@example.co.uk", "John Doe", UserRole.USER);
        when(appUserRepository.save(any(AppUser.class))).thenReturn(savedUser);

        AppUser result = appUserService.registerUser(request);
        assertThat(result.getEmail()).isEqualTo("john+test@example.co.uk");
    }

    // ==================== Concurrent Access Scenarios ====================

    @Test
    void handleConcurrentRegistrationWithSameEmail() {
        RegisterRequest request = new RegisterRequest();
        request.setEmail("john@example.com");
        request.setFullName("John Doe");
        request.setPassword("SecurePass123");

        // First call returns false, suggesting user doesn't exist
        when(appUserRepository.existsByEmailIgnoreCase("john@example.com"))
                .thenReturn(false);

        when(passwordEncoder.encode("SecurePass123")).thenReturn("hashed");

        // But then save fails due to constraint violation
        when(appUserRepository.save(any(AppUser.class)))
                .thenThrow(new RuntimeException("Unique constraint violation"));

        assertThatThrownBy(() -> appUserService.registerUser(request))
                .isInstanceOf(RuntimeException.class);
    }

    // ==================== Data Integrity Tests ====================

    @Test
    void handleStatementWithMissingRequiredFields() {
        Statement stmt = statement(1L, "DONE");
        stmt.setCustomerName(null);
        stmt.setStatus(null);

        when(statementRepository.findById(1L)).thenReturn(Optional.of(stmt));

        Optional<Statement> result = statementService.getStatement(1L);

        assertThat(result).isPresent();
        assertThat(result.get().getCustomerName()).isNull();
    }

    @Test
    void handleTransactionWithAllNullAmounts() {
        Transaction t = new Transaction();
        t.setId(1L);
        t.setDescription("All nulls");
        t.setDebit(null);
        t.setCredit(null);
        t.setBalance(null);

        when(transactionRepository.findByStatementIdOrderByDateDesc(1L)).thenReturn(List.of(t));

        List<Transaction> result = statementService.getTransactions(1L);

        assertThat(result).hasSize(1);
        assertThat(result.get(0).getDebit()).isNull();
        assertThat(result.get(0).getCredit()).isNull();
        assertThat(result.get(0).getBalance()).isNull();
    }
}
