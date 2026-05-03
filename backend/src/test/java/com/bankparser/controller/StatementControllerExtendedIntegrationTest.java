package com.bankparser.controller;

import com.bankparser.dto.StatementUploadRequest;
import com.bankparser.model.Statement;
import com.bankparser.model.Transaction;
import com.bankparser.service.StatementService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.mock.web.MockMultipartFile;

import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Extended integration tests for StatementController.
 * Tests file upload, transaction retrieval, insights, export, and deletion.
 */
@ExtendWith(MockitoExtension.class)
class StatementControllerExtendedIntegrationTest {

    @Mock
    StatementService service;

    StatementController controller;
    ObjectMapper objectMapper;

    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper();
        controller = new StatementController(service, objectMapper);
    }

    private Statement statement(Long id, String status, String customerName) {
        Statement s = new Statement();
        s.setId(id);
        s.setStatus(status);
        s.setCustomerName(customerName);
        return s;
    }

    private Transaction transaction(Long id, String description, String category, Double debit, Double credit) {
        Transaction t = new Transaction();
        t.setId(id);
        t.setDescription(description);
        t.setCategory(category);
        t.setDebit(debit);
        t.setCredit(credit);
        t.setDate("2024-01-15");
        t.setReference("REF123");
        return t;
    }

    // ==================== File Upload Tests ====================

    @Test
    void uploadFileSucceeds() throws Exception {
        MockMultipartFile file = new MockMultipartFile(
                "file",
                "statement.pdf",
                MediaType.APPLICATION_PDF_VALUE,
                "pdf_content".getBytes()
        );

        StatementUploadRequest metadata = new StatementUploadRequest();
        metadata.setCustomerName("John Doe");
        metadata.setBankName("HDFC");
        metadata.setAccountNumber("1234567890");
        String metadataJson = objectMapper.writeValueAsString(metadata);

        Statement uploadedStatement = statement(1L, "PROCESSING", "John Doe");
        when(service.uploadAndParse(file, metadata)).thenReturn(uploadedStatement);

        ResponseEntity<?> response = controller.upload(file, metadataJson);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).isInstanceOf(Statement.class);

        Statement result = (Statement) response.getBody();
        assertThat(result.getId()).isEqualTo(1L);
        assertThat(result.getCustomerName()).isEqualTo("John Doe");

        verify(service).uploadAndParse(file, metadata);
    }

    @Test
    void uploadFileFailsWithInvalidMetadata() throws Exception {
        MockMultipartFile file = new MockMultipartFile(
                "file",
                "statement.pdf",
                MediaType.APPLICATION_PDF_VALUE,
                "pdf_content".getBytes()
        );

        String invalidMetadataJson = "{invalid json}";

        ResponseEntity<?> response = controller.upload(file, invalidMetadataJson);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.INTERNAL_SERVER_ERROR);

        @SuppressWarnings("unchecked")
        Map<String, String> body = (Map<String, String>) response.getBody();
        assertThat(body.get("error")).isNotEmpty();
    }

    @Test
    void uploadFileHandlesServiceException() throws Exception {
        MockMultipartFile file = new MockMultipartFile(
                "file",
                "statement.pdf",
                MediaType.APPLICATION_PDF_VALUE,
                "pdf_content".getBytes()
        );

        StatementUploadRequest metadata = new StatementUploadRequest();
        metadata.setCustomerName("John Doe");
        String metadataJson = objectMapper.writeValueAsString(metadata);

        when(service.uploadAndParse(file, metadata))
                .thenThrow(new RuntimeException("File parse failed"));

        ResponseEntity<?> response = controller.upload(file, metadataJson);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.INTERNAL_SERVER_ERROR);

        @SuppressWarnings("unchecked")
        Map<String, String> body = (Map<String, String>) response.getBody();
        assertThat(body.get("error")).contains("parse failed");
    }

    // ==================== Transaction Retrieval Tests ====================

    @Test
    void getTransactionsReturnsListForValidStatement() {
        List<Transaction> transactions = List.of(
                transaction(1L, "Salary", "INCOME", null, 50000.0),
                transaction(2L, "Rent", "EXPENSES", 15000.0, null),
                transaction(3L, "Food", "FOOD", 500.0, null)
        );

        when(service.getTransactions(1L)).thenReturn(transactions);

        ResponseEntity<List<Transaction>> response = controller.transactions(1L);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).hasSize(3);
        assertThat(response.getBody().get(0).getCategory()).isEqualTo("INCOME");

        verify(service).getTransactions(1L);
    }

    @Test
    void getTransactionsReturnsEmptyListWhenNoTransactions() {
        when(service.getTransactions(99L)).thenReturn(List.of());

        ResponseEntity<List<Transaction>> response = controller.transactions(99L);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).isEmpty();
    }

    // ==================== Insights Tests ====================

    @Test
    void getInsightsSucceeds() {
        Map<String, Object> insights = Map.of(
                "totalCredit", 100000.0,
                "totalDebit", 45000.0,
                "averageTransaction", 1500.0,
                "categories", Map.of("INCOME", 100000, "EXPENSES", 45000)
        );

        when(service.getInsights(1L)).thenReturn(insights);

        ResponseEntity<?> response = controller.insights(1L);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).isEqualTo(insights);

        verify(service).getInsights(1L);
    }

    @Test
    void getInsightsHandlesError() {
        when(service.getInsights(99L))
                .thenThrow(new RuntimeException("Statement not found"));

        ResponseEntity<?> response = controller.insights(99L);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.INTERNAL_SERVER_ERROR);

        @SuppressWarnings("unchecked")
        Map<String, String> body = (Map<String, String>) response.getBody();
        assertThat(body.get("error")).contains("not found");
    }

    // ==================== Scorecard Tests ====================

    @Test
    void getScorecardSucceeds() {
        Map<String, Object> scorecard = Map.of(
                "creditScore", 750,
                "riskLevel", "LOW",
                "loanEligibility", "APPROVED",
                "monthlyAverage", 5000.0
        );

        when(service.getScorecard(1L)).thenReturn(scorecard);

        ResponseEntity<?> response = controller.scorecard(1L);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).isEqualTo(scorecard);

        verify(service).getScorecard(1L);
    }

    @Test
    void getScorecardHandlesError() {
        when(service.getScorecard(99L))
                .thenThrow(new RuntimeException("Analysis failed"));

        ResponseEntity<?> response = controller.scorecard(99L);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.INTERNAL_SERVER_ERROR);
    }

    // ==================== Export Tests ====================

    @Test
    void exportCsvSucceeds() {
        Statement stmt = statement(1L, "DONE", "John Doe");
        List<Transaction> transactions = List.of(
                transaction(1L, "Salary", "INCOME", null, 50000.0),
                transaction(2L, "Rent", "EXPENSES", 15000.0, null)
        );

        when(service.getTransactions(1L)).thenReturn(transactions);
        when(service.getStatement(1L)).thenReturn(Optional.of(stmt));

        ResponseEntity<byte[]> response = controller.exportCsv(1L);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getHeaders().getContentType()).isNotNull();
        assertThat(response.getHeaders().getContentDisposition().getFilename())
                .contains("statement_1")
                .contains("John_Doe");
        assertThat(response.getBody()).isNotEmpty();

        verify(service).getTransactions(1L);
        verify(service).getStatement(1L);
    }

    @Test
    void exportCsvHandlesStatementNotFound() {
        when(service.getStatement(99L)).thenReturn(Optional.empty());

        ResponseEntity<byte[]> response = controller.exportCsv(99L);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.INTERNAL_SERVER_ERROR);
    }

    @Test
    void exportCsvHandlesNullCustomerName() {
        Statement stmt = statement(2L, "DONE", null);
        List<Transaction> transactions = List.of(
                transaction(1L, "Salary", "INCOME", null, 50000.0)
        );

        when(service.getTransactions(2L)).thenReturn(transactions);
        when(service.getStatement(2L)).thenReturn(Optional.of(stmt));

        ResponseEntity<byte[]> response = controller.exportCsv(2L);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getHeaders().getContentDisposition().getFilename())
                .contains("statement_2")
                .contains("export");
    }

    // ==================== Deletion Tests ====================

    @Test
    void deleteStatementSucceeds() {
        ResponseEntity<Void> response = controller.delete(1L);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.NO_CONTENT);
        assertThat(response.getBody()).isNull();

        verify(service).deleteStatement(1L);
    }

    @Test
    void deleteNonExistentStatementStillReturns204() {
        // Service throws no error for non-existent deletion (idempotent)
        ResponseEntity<Void> response = controller.delete(99L);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.NO_CONTENT);

        verify(service).deleteStatement(99L);
    }

    // ==================== List Statements Tests ====================

    @Test
    void listStatementsWithDefaultScope() {
        List<Statement> statements = List.of(
                statement(1L, "DONE", "User 1"),
                statement(2L, "DONE", "User 2")
        );

        when(service.getStatements("mine")).thenReturn(statements);

        ResponseEntity<List<Statement>> response = controller.list("mine");

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).hasSize(2);

        verify(service).getStatements("mine");
    }

    @Test
    void listStatementsWithAllScope() {
        List<Statement> statements = List.of(
                statement(1L, "DONE", "User 1"),
                statement(2L, "PENDING", "User 2"),
                statement(3L, "DONE", "User 3")
        );

        when(service.getStatements("all")).thenReturn(statements);

        ResponseEntity<List<Statement>> response = controller.list("all");

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).hasSize(3);

        verify(service).getStatements("all");
    }

    // ==================== Get Statement Tests ====================

    @Test
    void getStatementByIdSucceeds() {
        Statement stmt = statement(1L, "DONE", "John Doe");
        when(service.getStatement(1L)).thenReturn(Optional.of(stmt));

        ResponseEntity<?> response = controller.get(1L);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).isInstanceOf(Statement.class);

        Statement result = (Statement) response.getBody();
        assertThat(result.getId()).isEqualTo(1L);

        verify(service).getStatement(1L);
    }

    @Test
    void getStatementByIdNotFound() {
        when(service.getStatement(99L)).thenReturn(Optional.empty());

        ResponseEntity<?> response = controller.get(99L);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
        assertThat(response.getBody()).isNull();
    }

    // ==================== Unlock Tests ====================

    @Test
    void unlockStatementSucceeds() {
        Statement stmt = statement(1L, "DONE", "John Doe");
        when(service.unlockWithPassword(1L, "password123")).thenReturn(stmt);

        ResponseEntity<?> response = controller.unlock(1L, Map.of("password", "password123"));

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);

        verify(service).unlockWithPassword(1L, "password123");
    }

    @Test
    void unlockStatementFailsWithWrongPassword() {
        when(service.unlockWithPassword(1L, "wrongpassword"))
                .thenThrow(new RuntimeException("Invalid password"));

        ResponseEntity<?> response = controller.unlock(1L, Map.of("password", "wrongpassword"));

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);

        @SuppressWarnings("unchecked")
        Map<String, String> body = (Map<String, String>) response.getBody();
        assertThat(body.get("error")).contains("Invalid password");
    }

    @Test
    void unlockWithEmptyPasswordMap() {
        Statement stmt = statement(1L, "DONE", "John Doe");
        when(service.unlockWithPassword(1L, "")).thenReturn(stmt);

        ResponseEntity<?> response = controller.unlock(1L, Map.of());

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);

        verify(service).unlockWithPassword(1L, "");
    }
}
