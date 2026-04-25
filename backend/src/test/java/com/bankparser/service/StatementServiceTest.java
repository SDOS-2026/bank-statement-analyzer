package com.bankparser.service;

import com.bankparser.model.AppUser;
import com.bankparser.model.Statement;
import com.bankparser.model.UserRole;
import com.bankparser.repository.StatementRepository;
import com.bankparser.repository.TransactionRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InOrder;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.client.RestTemplate;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class StatementServiceTest {

    @Mock
    StatementRepository statementRepo;

    @Mock
    TransactionRepository transactionRepo;

    @Mock
    RestTemplate restTemplate;

    @Mock
    AppUserService appUserService;

    StatementService service;

    @BeforeEach
    void setUp() {
        service = new StatementService(statementRepo, transactionRepo, restTemplate, new ObjectMapper(), appUserService);
    }

    private AppUser user(long id, UserRole role) {
        AppUser u = new AppUser();
        u.setId(id);
        u.setRole(role);
        u.setEmail("u@example.com");
        u.setFullName("U");
        u.setPasswordHash("x");
        return u;
    }

    private Statement statement(long id) {
        Statement s = new Statement();
        s.setId(id);
        s.setStatus("DONE");
        return s;
    }

    @Test
    void getStatementsReturnsOnlyOwnerDataForRegularUser() {
        AppUser current = user(11L, UserRole.USER);
        when(appUserService.getCurrentUser()).thenReturn(current);
        when(statementRepo.findAllByOwnerIdOrderByCreatedAtDesc(11L)).thenReturn(List.of(statement(1L)));

        List<Statement> result = service.getStatements("mine");

        assertThat(result).hasSize(1);
        verify(statementRepo).findAllByOwnerIdOrderByCreatedAtDesc(11L);
    }

    @Test
    void getStatementsReturnsAllForInternalScopeAll() {
        AppUser current = user(7L, UserRole.INTERNAL);
        when(appUserService.getCurrentUser()).thenReturn(current);
        when(statementRepo.findAllByOrderByCreatedAtDesc()).thenReturn(List.of(statement(1L), statement(2L)));

        List<Statement> result = service.getStatements("all");

        assertThat(result).hasSize(2);
        verify(statementRepo).findAllByOrderByCreatedAtDesc();
    }

    @Test
    void getStatementReturnsEmptyWhenNotAuthorizedOrMissing() {
        AppUser current = user(11L, UserRole.USER);
        when(appUserService.getCurrentUser()).thenReturn(current);
        when(statementRepo.findByIdAndOwnerId(99L, 11L)).thenReturn(Optional.empty());

        assertThat(service.getStatement(99L)).isEmpty();
    }

    @Test
    void deleteStatementRemovesTransactionsThenStatement() {
        AppUser current = user(3L, UserRole.INTERNAL);
        Statement s = statement(44L);
        when(appUserService.getCurrentUser()).thenReturn(current);
        when(statementRepo.findById(44L)).thenReturn(Optional.of(s));

        service.deleteStatement(44L);

        InOrder order = inOrder(transactionRepo, statementRepo);
        order.verify(transactionRepo).deleteByStatementId(44L);
        order.verify(statementRepo).deleteById(44L);
    }

    @Test
    void unlockRequiresPendingStatus() {
        AppUser current = user(3L, UserRole.INTERNAL);
        Statement s = statement(44L);
        s.setStatus("DONE");
        when(appUserService.getCurrentUser()).thenReturn(current);
        when(statementRepo.findById(44L)).thenReturn(Optional.of(s));

        assertThatThrownBy(() -> service.unlockWithPassword(44L, "secret"))
                .isInstanceOf(RuntimeException.class)
                .hasMessageContaining("not waiting for a password");
    }
}
