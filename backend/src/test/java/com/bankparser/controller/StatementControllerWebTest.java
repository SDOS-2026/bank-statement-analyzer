package com.bankparser.controller;

import com.bankparser.model.Statement;
import com.bankparser.model.Transaction;
import com.bankparser.service.StatementService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.List;
import java.util.Optional;

import static org.hamcrest.Matchers.containsString;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class StatementControllerWebTest {

    StatementService service;
    MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        service = mock(StatementService.class);
        mockMvc = MockMvcBuilders
                .standaloneSetup(new StatementController(service, new ObjectMapper()))
                .build();
    }

    @Test
    void uploadAcceptsMultipartFileAndMetadata() throws Exception {
        Statement statement = new Statement();
        statement.setId(7L);
        statement.setStatus("DONE");
        statement.setCustomerName("Asha");
        when(service.uploadAndParse(any(), any())).thenReturn(statement);

        MockMultipartFile file = new MockMultipartFile(
                "file", "statement.pdf", "application/pdf", "pdf".getBytes());
        MockMultipartFile metadata = new MockMultipartFile(
                "metadata", "", "application/json",
                """
                {"customerName":"Asha","bankName":"HDFC Bank","accountNumber":"1234"}
                """.getBytes());

        mockMvc.perform(multipart("/api/statements").file(file).file(metadata))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(7))
                .andExpect(jsonPath("$.status").value("DONE"))
                .andExpect(jsonPath("$.customerName").value("Asha"));
    }

    @Test
    void csvExportStreamsTransactionsWithAttachmentName() throws Exception {
        Statement statement = new Statement();
        statement.setId(4L);
        statement.setCustomerName("Asha Rao");
        Transaction transaction = new Transaction();
        transaction.setDate("2026-01-01");
        transaction.setDescription("Salary");
        transaction.setCategory("Income");
        transaction.setCredit(90000.0);
        transaction.setBalance(120000.0);

        when(service.getStatement(4L)).thenReturn(Optional.of(statement));
        when(service.getTransactions(4L)).thenReturn(List.of(transaction));

        mockMvc.perform(get("/api/statements/4/export/csv"))
                .andExpect(status().isOk())
                .andExpect(header().string("Content-Disposition", containsString("statement_4_Asha_Rao.csv")))
                .andExpect(content().contentType("text/csv"))
                .andExpect(content().string(containsString("Salary")))
                .andExpect(content().string(containsString("90000.00")));
    }
}
