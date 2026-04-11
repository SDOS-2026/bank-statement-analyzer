package com.bankparser.controller;

import com.bankparser.model.Statement;
import com.bankparser.model.Transaction;
import com.bankparser.service.StatementService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;

import java.util.*;

import static org.hamcrest.Matchers.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(StatementController.class)
class StatementControllerTest {

    @Autowired MockMvc mockMvc;
    @Autowired ObjectMapper objectMapper;
    @MockBean StatementService service;

    // ── helpers ───────────────────────────────────────────────────────────────

    private Statement statement(Long id, String status) {
        Statement s = new Statement();
        s.setId(id);
        s.setStatus(status);
        s.setCustomerName("Alice");
        s.setBankName("HDFC");
        return s;
    }

    private Transaction transaction(Long id, String date, String desc, Double debit) {
        Transaction t = new Transaction();
        t.setId(id);
        t.setDate(date);
        t.setDescription(desc);
        t.setDebit(debit);
        t.setCredit(null);
        t.setBalance(5000.0);
        t.setReference("REF" + id);
        t.setCategory("Food");
        t.setRowIndex(id.intValue() - 1);
        return t;
    }

    // ══════════════════════════════════════════════════════════════════════════
    //  GET /api/statements
    // ══════════════════════════════════════════════════════════════════════════

    @Nested
    @DisplayName("GET /api/statements")
    class ListEndpointTests {

        @Test
        @DisplayName("returns 200 with list of statements")
        void listReturns200() throws Exception {
            when(service.getAllStatements()).thenReturn(
                    List.of(statement(1L, "DONE"), statement(2L, "ERROR")));

            mockMvc.perform(get("/api/statements"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$", hasSize(2)))
                    .andExpect(jsonPath("$[0].id", is(1)))
                    .andExpect(jsonPath("$[1].status", is("ERROR")));
        }

        @Test
        @DisplayName("returns 200 with empty list when no statements exist")
        void emptyListReturns200() throws Exception {
            when(service.getAllStatements()).thenReturn(Collections.emptyList());

            mockMvc.perform(get("/api/statements"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$", hasSize(0)));
        }
    }

    // ══════════════════════════════════════════════════════════════════════════
    //  POST /api/statements
    // ══════════════════════════════════════════════════════════════════════════

    @Nested
    @DisplayName("POST /api/statements")
    class UploadEndpointTests {

        @Test
        @DisplayName("successful upload returns 200 with saved statement")
        void successfulUploadReturns200() throws Exception {
            Statement saved = statement(1L, "DONE");
            when(service.uploadAndParse(any(), any())).thenReturn(saved);

            MockMultipartFile file = new MockMultipartFile(
                    "file", "test.pdf", "application/pdf", new byte[]{1, 2, 3});
            String meta = objectMapper.writeValueAsString(Map.of(
                    "customerName", "Alice", "bankName", "HDFC",
                    "accountNumber", "ACC-001", "statementPeriod", "Jan-2025",
                    "analystName", "Tester", "notes", ""));

            mockMvc.perform(multipart("/api/statements")
                            .file(file)
                            .file(new MockMultipartFile("metadata", "", "text/plain", meta.getBytes())))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.id", is(1)))
                    .andExpect(jsonPath("$.status", is("DONE")));
        }

        @Test
        @DisplayName("service exception returns 500 with error body")
        void serviceExceptionReturns500() throws Exception {
            when(service.uploadAndParse(any(), any()))
                    .thenThrow(new RuntimeException("Unexpected failure"));

            MockMultipartFile file = new MockMultipartFile(
                    "file", "test.pdf", "application/pdf", new byte[]{1});
            String meta = objectMapper.writeValueAsString(Map.of("customerName", "Alice"));

            mockMvc.perform(multipart("/api/statements")
                            .file(file)
                            .file(new MockMultipartFile("metadata", "", "text/plain", meta.getBytes())))
                    .andExpect(status().isInternalServerError())
                    .andExpect(jsonPath("$.error", containsString("Unexpected failure")));
        }
    }

    // ══════════════════════════════════════════════════════════════════════════
    //  GET /api/statements/{id}
    // ══════════════════════════════════════════════════════════════════════════

    @Nested
    @DisplayName("GET /api/statements/{id}")
    class GetByIdTests {

        @Test
        @DisplayName("existing statement returns 200")
        void foundReturns200() throws Exception {
            when(service.getStatement(1L)).thenReturn(Optional.of(statement(1L, "DONE")));

            mockMvc.perform(get("/api/statements/1"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.id", is(1)))
                    .andExpect(jsonPath("$.status", is("DONE")));
        }

        @Test
        @DisplayName("missing statement returns 404")
        void notFoundReturns404() throws Exception {
            when(service.getStatement(99L)).thenReturn(Optional.empty());

            mockMvc.perform(get("/api/statements/99"))
                    .andExpect(status().isNotFound());
        }
    }

    // ══════════════════════════════════════════════════════════════════════════
    //  POST /api/statements/{id}/unlock
    // ══════════════════════════════════════════════════════════════════════════

    @Nested
    @DisplayName("POST /api/statements/{id}/unlock")
    class UnlockEndpointTests {

        @Test
        @DisplayName("successful unlock returns 200 with updated statement")
        void successfulUnlockReturns200() throws Exception {
            Statement unlocked = statement(1L, "DONE");
            when(service.unlockWithPassword(eq(1L), eq("secret"))).thenReturn(unlocked);

            mockMvc.perform(post("/api/statements/1/unlock")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"password\":\"secret\"}"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.status", is("DONE")));
        }

        @Test
        @DisplayName("service exception returns 400 with error body")
        void serviceExceptionReturns400() throws Exception {
            when(service.unlockWithPassword(anyLong(), anyString()))
                    .thenThrow(new RuntimeException("Statement not found"));

            mockMvc.perform(post("/api/statements/99/unlock")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"password\":\"pass\"}"))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.error", containsString("Statement not found")));
        }

        @Test
        @DisplayName("empty password body defaults gracefully (no NPE)")
        void emptyPasswordBody() throws Exception {
            Statement stmt = statement(1L, "PENDING_PASSWORD");
            when(service.unlockWithPassword(eq(1L), eq(""))).thenReturn(stmt);

            mockMvc.perform(post("/api/statements/1/unlock")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{}"))
                    .andExpect(status().isOk());
        }
    }

    // ══════════════════════════════════════════════════════════════════════════
    //  GET /api/statements/{id}/transactions
    // ══════════════════════════════════════════════════════════════════════════

    @Nested
    @DisplayName("GET /api/statements/{id}/transactions")
    class TransactionsEndpointTests {

        @Test
        @DisplayName("returns 200 with list of transactions")
        void returnsTransactions() throws Exception {
            when(service.getTransactions(1L)).thenReturn(
                    List.of(transaction(1L, "2025-01-01", "ATM", 500.0),
                            transaction(2L, "2025-01-02", "Salary", null)));

            mockMvc.perform(get("/api/statements/1/transactions"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$", hasSize(2)))
                    .andExpect(jsonPath("$[0].description", is("ATM")))
                    .andExpect(jsonPath("$[1].description", is("Salary")));
        }

        @Test
        @DisplayName("returns 200 with empty list when no transactions")
        void emptyTransactions() throws Exception {
            when(service.getTransactions(1L)).thenReturn(Collections.emptyList());

            mockMvc.perform(get("/api/statements/1/transactions"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$", hasSize(0)));
        }
    }

    // ══════════════════════════════════════════════════════════════════════════
    //  GET /api/statements/{id}/insights
    // ══════════════════════════════════════════════════════════════════════════

    @Nested
    @DisplayName("GET /api/statements/{id}/insights")
    class InsightsEndpointTests {

        @Test
        @DisplayName("returns 200 with insights map")
        void returnsInsights() throws Exception {
            when(service.getInsights(1L)).thenReturn(Map.of("avg_debit", 3000));

            mockMvc.perform(get("/api/statements/1/insights"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.avg_debit", is(3000)));
        }

        @Test
        @DisplayName("returns 200 with empty map when no insights stored")
        void returnsEmptyInsights() throws Exception {
            when(service.getInsights(1L)).thenReturn(Collections.emptyMap());

            mockMvc.perform(get("/api/statements/1/insights"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$", anEmptyMap()));
        }

        @Test
        @DisplayName("service exception returns 500")
        void serviceExceptionReturns500() throws Exception {
            when(service.getInsights(99L)).thenThrow(new RuntimeException("not found"));

            mockMvc.perform(get("/api/statements/99/insights"))
                    .andExpect(status().isInternalServerError())
                    .andExpect(jsonPath("$.error", containsString("not found")));
        }
    }

    // ══════════════════════════════════════════════════════════════════════════
    //  GET /api/statements/{id}/scorecard
    // ══════════════════════════════════════════════════════════════════════════

    @Nested
    @DisplayName("GET /api/statements/{id}/scorecard")
    class ScorecardEndpointTests {

        @Test
        @DisplayName("returns 200 with scorecard map")
        void returnsScorecardMap() throws Exception {
            when(service.getScorecard(1L)).thenReturn(Map.of("score", 85));

            mockMvc.perform(get("/api/statements/1/scorecard"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.score", is(85)));
        }

        @Test
        @DisplayName("service exception returns 500")
        void serviceExceptionReturns500() throws Exception {
            when(service.getScorecard(99L)).thenThrow(new RuntimeException("not found"));

            mockMvc.perform(get("/api/statements/99/scorecard"))
                    .andExpect(status().isInternalServerError());
        }
    }

    // ══════════════════════════════════════════════════════════════════════════
    //  GET /api/statements/{id}/export/csv
    // ══════════════════════════════════════════════════════════════════════════

    @Nested
    @DisplayName("GET /api/statements/{id}/export/csv")
    class ExportCsvTests {

        @Test
        @DisplayName("returns 200 with CSV content-type and attachment header")
        void csvResponseHeaders() throws Exception {
            Statement stmt = statement(1L, "DONE");
            when(service.getStatement(1L)).thenReturn(Optional.of(stmt));
            when(service.getTransactions(1L)).thenReturn(
                    List.of(transaction(1L, "2025-01-01", "ATM Withdrawal", 500.0)));

            mockMvc.perform(get("/api/statements/1/export/csv"))
                    .andExpect(status().isOk())
                    .andExpect(header().string("Content-Type", containsString("text/csv")))
                    .andExpect(header().string("Content-Disposition", containsString("attachment")))
                    .andExpect(header().string("Content-Disposition", containsString("statement_1_")));
        }

        @Test
        @DisplayName("CSV body contains header row and transaction row")
        void csvBodyContent() throws Exception {
            Statement stmt = statement(1L, "DONE");
            when(service.getStatement(1L)).thenReturn(Optional.of(stmt));
            when(service.getTransactions(1L)).thenReturn(
                    List.of(transaction(1L, "2025-01-01", "ATM Withdrawal", 500.0)));

            byte[] body = mockMvc.perform(get("/api/statements/1/export/csv"))
                    .andExpect(status().isOk())
                    .andReturn().getResponse().getContentAsByteArray();

            String csv = new String(body);
            assertThat(csv).contains("Date");
            assertThat(csv).contains("Description");
            assertThat(csv).contains("ATM Withdrawal");
            assertThat(csv).contains("500.00");
        }

        @Test
        @DisplayName("CSV export with empty transactions still returns 200")
        void emptyTransactionsCsv() throws Exception {
            Statement stmt = statement(1L, "DONE");
            when(service.getStatement(1L)).thenReturn(Optional.of(stmt));
            when(service.getTransactions(1L)).thenReturn(Collections.emptyList());

            mockMvc.perform(get("/api/statements/1/export/csv"))
                    .andExpect(status().isOk());
        }
    }

    // ══════════════════════════════════════════════════════════════════════════
    //  DELETE /api/statements/{id}
    // ══════════════════════════════════════════════════════════════════════════

    @Nested
    @DisplayName("DELETE /api/statements/{id}")
    class DeleteEndpointTests {

        @Test
        @DisplayName("returns 204 No Content on successful delete")
        void deleteReturns204() throws Exception {
            doNothing().when(service).deleteStatement(1L);

            mockMvc.perform(delete("/api/statements/1"))
                    .andExpect(status().isNoContent());

            verify(service).deleteStatement(1L);
        }

        @Test
        @DisplayName("delegates correct id to service")
        void correctIdPassedToService() throws Exception {
            doNothing().when(service).deleteStatement(42L);

            mockMvc.perform(delete("/api/statements/42"))
                    .andExpect(status().isNoContent());

            verify(service).deleteStatement(42L);
        }
    }
}
