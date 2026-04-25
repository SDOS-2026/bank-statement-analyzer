package com.bankparser.controller;

import com.bankparser.model.Statement;
import com.bankparser.service.StatementService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.ResponseEntity;

import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class StatementControllerTest {

    @Mock
    StatementService service;

    StatementController controller;

    @BeforeEach
    void setUp() {
        controller = new StatementController(service, new ObjectMapper());
    }

    private Statement statement(Long id, String status) {
        Statement s = new Statement();
        s.setId(id);
        s.setStatus(status);
        s.setCustomerName("Alice");
        return s;
    }

    @Test
    void listDefaultsToMineScope() {
        when(service.getStatements("mine")).thenReturn(List.of(statement(1L, "DONE")));

        ResponseEntity<List<Statement>> response = controller.list("mine");

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(response.getBody()).hasSize(1);
        verify(service).getStatements("mine");
    }

    @Test
    void getByIdNotFound() {
        when(service.getStatement(99L)).thenReturn(Optional.empty());

        ResponseEntity<?> response = controller.get(99L);

        assertThat(response.getStatusCode().value()).isEqualTo(404);
        verify(service).getStatement(99L);
    }

    @Test
    void unlockWithEmptyPasswordBodyReturns200() throws Exception {
        when(service.unlockWithPassword(1L, "")).thenReturn(statement(1L, "DONE"));

        ResponseEntity<?> response = controller.unlock(1L, Map.of());

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
        verify(service).unlockWithPassword(1L, "");
    }
}
