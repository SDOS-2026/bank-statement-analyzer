package com.bankparser.controller;

import com.bankparser.model.Statement;
import com.bankparser.model.Transaction;
import com.bankparser.service.StatementService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.*;
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
import static org.assertj.core.api.Assertions.assertThat; // ✅ FIXED
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(StatementController.class)
class StatementControllerTest {

    @Autowired MockMvc mockMvc;
    @Autowired ObjectMapper objectMapper;
    @MockBean StatementService service;

    // ── helpers ─────────────────────────────────────────

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

    // ════════════════════════════════════════════════════
    // GET /api/statements
    // ════════════════════════════════════════════════════

    @Test
    void listReturns200() throws Exception {
        when(service.getAllStatements()).thenReturn(
                List.of(statement(1L, "DONE"), statement(2L, "ERROR")));

        mockMvc.perform(get("/api/statements"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(2)));

        verify(service).getAllStatements(); // ✅ added
    }

    // ════════════════════════════════════════════════════
    // POST /api/statements
    // ════════════════════════════════════════════════════

    @Test
    void uploadReturns200() throws Exception {
        Statement saved = statement(1L, "DONE");
        when(service.uploadAndParse(any(), any())).thenReturn(saved);

        MockMultipartFile file = new MockMultipartFile(
                "file", "test.pdf", "application/pdf", new byte[]{1});

        String meta = objectMapper.writeValueAsString(Map.of("customerName", "Alice"));

        mockMvc.perform(multipart("/api/statements")
                        .file(file)
                        .file(new MockMultipartFile(
                                "metadata",
                                "",
                                MediaType.APPLICATION_JSON_VALUE, // ✅ FIXED
                                meta.getBytes())))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id", is(1)));

        verify(service).uploadAndParse(any(), any());
    }

    // ════════════════════════════════════════════════════
    // GET by ID
    // ════════════════════════════════════════════════════

    @Test
    void getByIdNotFound() throws Exception {
        when(service.getStatement(99L)).thenReturn(Optional.empty());

        mockMvc.perform(get("/api/statements/99"))
                .andExpect(status().isNotFound());

        verify(service).getStatement(99L);
    }

    // ════════════════════════════════════════════════════
    // Unlock
    // ════════════════════════════════════════════════════

    @Test
    void unlockHandlesEmptyBody() throws Exception {
        when(service.unlockWithPassword(eq(1L), eq("")))
                .thenReturn(statement(1L, "DONE"));

        mockMvc.perform(post("/api/statements/1/unlock")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{}"))
                .andExpect(status().isOk());

        verify(service).unlockWithPassword(1L, "");
    }

    // ════════════════════════════════════════════════════
    // CSV Export
    // ════════════════════════════════════════════════════

    @Test
    void csvContentIsValid() throws Exception {
        Statement stmt = statement(1L, "DONE");

        when(service.getStatement(1L)).thenReturn(Optional.of(stmt));
        when(service.getTransactions(1L)).thenReturn(
                List.of(transaction(1L, "2025-01-01", "ATM Withdrawal", 500.0)));

        String csv = mockMvc.perform(get("/api/statements/1/export/csv"))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();

        // ✅ Stronger assertions
        assertThat(csv).contains("Date,Description");
        assertThat(csv).contains("ATM Withdrawal");
        assertThat(csv).contains("500.00");

        verify(service).getTransactions(1L);
    }

    // ════════════════════════════════════════════════════
    // DELETE
    // ════════════════════════════════════════════════════

    @Test
    void deleteCallsService() throws Exception {
        doNothing().when(service).deleteStatement(1L);

        mockMvc.perform(delete("/api/statements/1"))
                .andExpect(status().isNoContent());

        verify(service, times(1)).deleteStatement(1L);
    }
}