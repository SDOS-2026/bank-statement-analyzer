package com.bankparser.service;

import com.bankparser.dto.StatementUploadRequest;
import com.bankparser.model.Statement;
import com.bankparser.model.Transaction;
import com.bankparser.repository.StatementRepository;
import com.bankparser.repository.TransactionRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.*;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.*;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.util.*;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class StatementServiceTest {

    @Mock StatementRepository statementRepo;
    @Mock TransactionRepository transactionRepo;
    @Mock RestTemplate restTemplate;
    @Mock MultipartFile mockFile;

    // Use a real ObjectMapper so JSON serialisation actually works
    ObjectMapper objectMapper = new ObjectMapper();

    StatementService service;

    @BeforeEach
    void setUp() throws Exception {
        service = new StatementService(statementRepo, transactionRepo, restTemplate, objectMapper);
        // Inject the @Value field manually (no Spring context in unit tests)
        var field = StatementService.class.getDeclaredField("parserUrl");
        field.setAccessible(true);
        field.set(service, "http://localhost:5050");
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private StatementUploadRequest buildMeta(String customer, String bank) {
        StatementUploadRequest req = new StatementUploadRequest();
        req.setCustomerName(customer);
        req.setBankName(bank);
        req.setAccountNumber("ACC-001");
        req.setStatementPeriod("Jan-2025");
        req.setAnalystName("Tester");
        req.setNotes("Test note");
        return req;
    }

    private Statement savedStatement(Long id, String status) {
        Statement s = new Statement();
        s.setId(id);
        s.setStatus(status);
        return s;
    }

    private String successParserResponse(int txnCount) throws Exception {
        Map<String, Object> meta = new LinkedHashMap<>();
        meta.put("bank", "HDFC");
        meta.put("engine", "pdfplumber");
        meta.put("total_rows", txnCount);
        meta.put("balance_mismatches", 0);
        meta.put("confidence", 0.95);
        meta.put("debit_total", 5000.0);
        meta.put("credit_total", 8000.0);

        List<Map<String, Object>> txns = new ArrayList<>();
        for (int i = 0; i < txnCount; i++) {
            Map<String, Object> t = new LinkedHashMap<>();
            t.put("Date", "2025-01-0" + (i + 1));
            t.put("Description", "TXN-" + i);
            t.put("Debit", 100.0 * (i + 1));
            t.put("Credit", null);
            t.put("Balance", 9000.0 - 100.0 * (i + 1));
            t.put("Reference", "REF" + i);
            t.put("Category", "Food");
            txns.add(t);
        }

        Map<String, Object> resp = new LinkedHashMap<>();
        resp.put("status", "success");
        resp.put("file_key", "key-abc");
        resp.put("meta", meta);
        resp.put("transactions", txns);
        resp.put("insights", Map.of("avg_monthly_debit", 5000));
        resp.put("scorecard", Map.of("score", 72));
        return objectMapper.writeValueAsString(resp);
    }

    // ══════════════════════════════════════════════════════════════════════════
    //  uploadAndParse()
    // ══════════════════════════════════════════════════════════════════════════

    @Nested
    @DisplayName("uploadAndParse()")
    class UploadAndParseTests {

        @BeforeEach
        void setupFile() throws Exception {
            when(mockFile.getOriginalFilename()).thenReturn("statement.pdf");
            when(mockFile.getBytes()).thenReturn(new byte[]{1, 2, 3});
        }

        @Test
        @DisplayName("detects file type PDF for .pdf extension")
        void fileTypePdf() throws Exception {
            stubParserSuccess(2);
            Statement result = service.uploadAndParse(mockFile, buildMeta("Alice", "HDFC"));
            assertThat(result.getFileType()).isEqualTo("PDF");
        }

        @Test
        @DisplayName("detects file type XLSX for .xlsx extension")
        void fileTypeXlsx() throws Exception {
            when(mockFile.getOriginalFilename()).thenReturn("data.xlsx");
            stubParserSuccess(1);
            Statement result = service.uploadAndParse(mockFile, buildMeta("Bob", "SBI"));
            assertThat(result.getFileType()).isEqualTo("XLSX");
        }

        @Test
        @DisplayName("detects file type XLS for .xls extension")
        void fileTypeXls() throws Exception {
            when(mockFile.getOriginalFilename()).thenReturn("data.xls");
            stubParserSuccess(1);
            Statement result = service.uploadAndParse(mockFile, buildMeta("Bob", "SBI"));
            assertThat(result.getFileType()).isEqualTo("XLS");
        }

        @Test
        @DisplayName("detects file type CSV for .csv extension")
        void fileTypeCsv() throws Exception {
            when(mockFile.getOriginalFilename()).thenReturn("txns.csv");
            stubParserSuccess(0);
            Statement result = service.uploadAndParse(mockFile, buildMeta("Carol", "ICICI"));
            assertThat(result.getFileType()).isEqualTo("CSV");
        }

        @Test
        @DisplayName("detects file type ODS for .ods extension")
        void fileTypeOds() throws Exception {
            when(mockFile.getOriginalFilename()).thenReturn("file.ods");
            stubParserSuccess(0);
            Statement result = service.uploadAndParse(mockFile, buildMeta("Dave", "Axis"));
            assertThat(result.getFileType()).isEqualTo("ODS");
        }

        @Test
        @DisplayName("copies metadata from upload request to Statement")
        void persistsMetadata() throws Exception {
            stubParserSuccess(1);
            Statement result = service.uploadAndParse(mockFile, buildMeta("Alice", "HDFC"));
            assertThat(result.getCustomerName()).isEqualTo("Alice");
            assertThat(result.getBankName()).isEqualTo("HDFC");
            assertThat(result.getAccountNumber()).isEqualTo("ACC-001");
            assertThat(result.getStatementPeriod()).isEqualTo("Jan-2025");
            assertThat(result.getAnalystName()).isEqualTo("Tester");
            assertThat(result.getNotes()).isEqualTo("Test note");
        }

        @Test
        @DisplayName("successful parse: status = DONE, meta fields populated")
        void successfulParseSetsStatusDoneAndMeta() throws Exception {
            stubParserSuccess(3);
            Statement result = service.uploadAndParse(mockFile, buildMeta("Alice", "HDFC"));
            assertThat(result.getStatus()).isEqualTo("DONE");
            assertThat(result.getDetectedBank()).isEqualTo("HDFC");
            assertThat(result.getEngineUsed()).isEqualTo("pdfplumber");
            assertThat(result.getConfidence()).isEqualTo(0.95);
            assertThat(result.getDebitTotal()).isEqualTo(5000.0);
            assertThat(result.getCreditTotal()).isEqualTo(8000.0);
            assertThat(result.getFileKey()).isEqualTo("key-abc");
        }

        @Test
        @DisplayName("successful parse: transactions are saved via saveAll")
        void successfulParseSavesTransactions() throws Exception {
            stubParserSuccess(3);
            service.uploadAndParse(mockFile, buildMeta("Alice", "HDFC"));
            ArgumentCaptor<List> captor = ArgumentCaptor.forClass(List.class);
            verify(transactionRepo).saveAll(captor.capture());
            assertThat(captor.getValue()).hasSize(3);
        }

        @Test
        @DisplayName("successful parse: insights and scorecard JSON stored on statement")
        void insightsAndScorecardJsonStored() throws Exception {
            stubParserSuccess(1);
            Statement result = service.uploadAndParse(mockFile, buildMeta("Alice", "HDFC"));
            assertThat(result.getInsightsJson()).contains("avg_monthly_debit");
            assertThat(result.getScorecardJson()).contains("score");
        }

        @Test
        @DisplayName("parser throws RuntimeException: status = ERROR with message")
        void parserExceptionSetsStatusError() throws Exception {
            when(restTemplate.postForEntity(anyString(), any(), eq(String.class)))
                    .thenThrow(new RuntimeException("Connection refused"));
            when(statementRepo.save(any())).thenAnswer(inv -> withId(inv.getArgument(0), 1L));

            Statement result = service.uploadAndParse(mockFile, buildMeta("Alice", "HDFC"));

            assertThat(result.getStatus()).isEqualTo("ERROR");
            assertThat(result.getErrorMessage()).contains("Connection refused");
        }

        @Test
        @DisplayName("parser returns password_required: status = PENDING_PASSWORD")
        void parserPasswordRequired() throws Exception {
            String json = objectMapper.writeValueAsString(
                    Map.of("status", "password_required", "file_key", "key-xyz"));
            when(restTemplate.postForEntity(anyString(), any(), eq(String.class)))
                    .thenReturn(new ResponseEntity<>(json, HttpStatus.OK));
            when(statementRepo.save(any())).thenAnswer(inv -> withId(inv.getArgument(0), 2L));

            Statement result = service.uploadAndParse(mockFile, buildMeta("Alice", "HDFC"));

            assertThat(result.getStatus()).isEqualTo("PENDING_PASSWORD");
        }

        @Test
        @DisplayName("parser returns unknown status: status = ERROR with message")
        void parserUnknownStatus() throws Exception {
            String json = objectMapper.writeValueAsString(
                    Map.of("status", "unsupported_format", "message", "Cannot parse this file"));
            when(restTemplate.postForEntity(anyString(), any(), eq(String.class)))
                    .thenReturn(new ResponseEntity<>(json, HttpStatus.OK));
            when(statementRepo.save(any())).thenAnswer(inv -> withId(inv.getArgument(0), 3L));

            Statement result = service.uploadAndParse(mockFile, buildMeta("Alice", "HDFC"));

            assertThat(result.getStatus()).isEqualTo("ERROR");
            assertThat(result.getErrorMessage()).contains("Cannot parse this file");
        }

        @Test
        @DisplayName("statementRepo.save() is called exactly twice (initial persist + final update)")
        void saveCalledTwice() throws Exception {
            stubParserSuccess(1);
            service.uploadAndParse(mockFile, buildMeta("Alice", "HDFC"));
            verify(statementRepo, times(2)).save(any(Statement.class));
        }

        @Test
        @DisplayName("initial status before calling parser is PROCESSING")
        void initialStatusIsProcessing() throws Exception {
            stubParserSuccess(1);
            ArgumentCaptor<Statement> captor = ArgumentCaptor.forClass(Statement.class);

            service.uploadAndParse(mockFile, buildMeta("Alice", "HDFC"));

            // The first save() call should have status PROCESSING
            verify(statementRepo, times(2)).save(captor.capture());
            assertThat(captor.getAllValues().get(0).getStatus()).isEqualTo("PROCESSING");
        }

        // ── stub helpers ──────────────────────────────────────────────────────

        void stubParserSuccess(int txnCount) throws Exception {
            String json = successParserResponse(txnCount);
            when(restTemplate.postForEntity(anyString(), any(), eq(String.class)))
                    .thenReturn(new ResponseEntity<>(json, HttpStatus.OK));
            when(statementRepo.save(any())).thenAnswer(inv -> withId(inv.getArgument(0), 1L));
        }
    }

    // ══════════════════════════════════════════════════════════════════════════
    //  unlockWithPassword()
    // ══════════════════════════════════════════════════════════════════════════

    @Nested
    @DisplayName("unlockWithPassword()")
    class UnlockWithPasswordTests {

        @Test
        @DisplayName("throws RuntimeException when statement does not exist")
        void statementNotFound() {
            when(statementRepo.findById(99L)).thenReturn(Optional.empty());
            assertThatThrownBy(() -> service.unlockWithPassword(99L, "pass"))
                    .isInstanceOf(RuntimeException.class)
                    .hasMessageContaining("Statement not found: 99");
        }

        @Test
        @DisplayName("throws RuntimeException when statement status is not PENDING_PASSWORD")
        void notPendingPassword() {
            when(statementRepo.findById(1L)).thenReturn(Optional.of(savedStatement(1L, "DONE")));
            assertThatThrownBy(() -> service.unlockWithPassword(1L, "pass"))
                    .isInstanceOf(RuntimeException.class)
                    .hasMessageContaining("not waiting for a password");
        }

        @Test
        @DisplayName("correct password: status becomes DONE")
        void successfulUnlock() throws Exception {
            Statement stmt = savedStatement(1L, "PENDING_PASSWORD");
            stmt.setFileKey("key-abc");
            when(statementRepo.findById(1L)).thenReturn(Optional.of(stmt));

            String json = successParserResponse(2);
            when(restTemplate.postForEntity(anyString(), any(), eq(String.class)))
                    .thenReturn(new ResponseEntity<>(json, HttpStatus.OK));
            when(statementRepo.save(any())).thenAnswer(inv -> inv.getArgument(0));

            Statement result = service.unlockWithPassword(1L, "correct-pass");
            assertThat(result.getStatus()).isEqualTo("DONE");
        }

        @Test
        @DisplayName("wrong password: status stays PENDING_PASSWORD with error message")
        void wrongPassword() throws Exception {
            Statement stmt = savedStatement(1L, "PENDING_PASSWORD");
            stmt.setFileKey("key-abc");
            when(statementRepo.findById(1L)).thenReturn(Optional.of(stmt));

            String json = objectMapper.writeValueAsString(Map.of("status", "wrong_password"));
            when(restTemplate.postForEntity(anyString(), any(), eq(String.class)))
                    .thenReturn(new ResponseEntity<>(json, HttpStatus.OK));
            when(statementRepo.save(any())).thenAnswer(inv -> inv.getArgument(0));

            Statement result = service.unlockWithPassword(1L, "wrong");
            assertThat(result.getStatus()).isEqualTo("PENDING_PASSWORD");
            assertThat(result.getErrorMessage()).contains("Wrong password");
        }

        @Test
        @DisplayName("parser exception during unlock preserves PENDING_PASSWORD status")
        void parserExceptionPreservesPendingPassword() throws Exception {
            Statement stmt = savedStatement(1L, "PENDING_PASSWORD");
            stmt.setFileKey("key-abc");
            when(statementRepo.findById(1L)).thenReturn(Optional.of(stmt));
            when(restTemplate.postForEntity(anyString(), any(), eq(String.class)))
                    .thenThrow(new RuntimeException("timeout"));
            when(statementRepo.save(any())).thenAnswer(inv -> inv.getArgument(0));

            Statement result = service.unlockWithPassword(1L, "pass");
            assertThat(result.getStatus()).isEqualTo("PENDING_PASSWORD");
        }
    }

    // ══════════════════════════════════════════════════════════════════════════
    //  CRUD operations
    // ══════════════════════════════════════════════════════════════════════════

    @Nested
    @DisplayName("CRUD operations")
    class CrudTests {

        @Test
        @DisplayName("getAllStatements() delegates to repository and returns full list")
        void getAllStatements() {
            List<Statement> list = List.of(savedStatement(1L, "DONE"), savedStatement(2L, "ERROR"));
            when(statementRepo.findAllByOrderByCreatedAtDesc()).thenReturn(list);
            assertThat(service.getAllStatements()).hasSize(2);
            verify(statementRepo).findAllByOrderByCreatedAtDesc();
        }

        @Test
        @DisplayName("getStatement() returns present Optional when found")
        void getStatementFound() {
            when(statementRepo.findById(5L)).thenReturn(Optional.of(savedStatement(5L, "DONE")));
            Optional<Statement> result = service.getStatement(5L);
            assertThat(result).isPresent();
            assertThat(result.get().getId()).isEqualTo(5L);
        }

        @Test
        @DisplayName("getStatement() returns empty Optional when not found")
        void getStatementNotFound() {
            when(statementRepo.findById(99L)).thenReturn(Optional.empty());
            assertThat(service.getStatement(99L)).isEmpty();
        }

        @Test
        @DisplayName("getTransactions() delegates to transaction repository")
        void getTransactions() {
            Transaction tx = new Transaction();
            tx.setId(1L);
            when(transactionRepo.findByStatementIdOrderByRowIndex(3L)).thenReturn(List.of(tx));
            List<Transaction> result = service.getTransactions(3L);
            assertThat(result).hasSize(1);
            verify(transactionRepo).findByStatementIdOrderByRowIndex(3L);
        }

        @Test
        @DisplayName("deleteStatement() deletes transactions first, then statement")
        void deleteOrderIsTransactionsThenStatement() {
            service.deleteStatement(7L);
            InOrder order = inOrder(transactionRepo, statementRepo);
            order.verify(transactionRepo).deleteByStatementId(7L);
            order.verify(statementRepo).deleteById(7L);
        }
    }

    // ══════════════════════════════════════════════════════════════════════════
    //  getInsights() and getScorecard()
    // ══════════════════════════════════════════════════════════════════════════

    @Nested
    @DisplayName("getInsights() and getScorecard()")
    class InsightsScorecardTests {

        @Test
        @DisplayName("getInsights() returns empty map when insightsJson is null")
        void insightsNullJson() throws Exception {
            Statement stmt = savedStatement(1L, "DONE");
            when(statementRepo.findById(1L)).thenReturn(Optional.of(stmt));
            assertThat(service.getInsights(1L)).isEmpty();
        }

        @Test
        @DisplayName("getInsights() returns empty map when insightsJson is blank")
        void insightsBlankJson() throws Exception {
            Statement stmt = savedStatement(1L, "DONE");
            stmt.setInsightsJson("   ");
            when(statementRepo.findById(1L)).thenReturn(Optional.of(stmt));
            assertThat(service.getInsights(1L)).isEmpty();
        }

        @Test
        @DisplayName("getInsights() correctly parses stored JSON")
        void insightsParsesJson() throws Exception {
            Statement stmt = savedStatement(1L, "DONE");
            stmt.setInsightsJson("{\"avg_debit\": 3000}");
            when(statementRepo.findById(1L)).thenReturn(Optional.of(stmt));
            Map<String, Object> result = service.getInsights(1L);
            assertThat(result).containsKey("avg_debit");
            assertThat(result.get("avg_debit")).isEqualTo(3000);
        }

        @Test
        @DisplayName("getInsights() throws RuntimeException when statement not found")
        void insightsStatementNotFound() {
            when(statementRepo.findById(99L)).thenReturn(Optional.empty());
            assertThatThrownBy(() -> service.getInsights(99L))
                    .isInstanceOf(RuntimeException.class)
                    .hasMessageContaining("Statement not found");
        }

        @Test
        @DisplayName("getScorecard() returns empty map when scorecardJson is null")
        void scorecardNullJson() throws Exception {
            Statement stmt = savedStatement(2L, "DONE");
            when(statementRepo.findById(2L)).thenReturn(Optional.of(stmt));
            assertThat(service.getScorecard(2L)).isEmpty();
        }

        @Test
        @DisplayName("getScorecard() correctly parses stored JSON")
        void scorecardParsesJson() throws Exception {
            Statement stmt = savedStatement(2L, "DONE");
            stmt.setScorecardJson("{\"score\": 85}");
            when(statementRepo.findById(2L)).thenReturn(Optional.of(stmt));
            Map<String, Object> result = service.getScorecard(2L);
            assertThat(result.get("score")).isEqualTo(85);
        }

        @Test
        @DisplayName("getScorecard() throws RuntimeException when statement not found")
        void scorecardStatementNotFound() {
            when(statementRepo.findById(99L)).thenReturn(Optional.empty());
            assertThatThrownBy(() -> service.getScorecard(99L))
                    .isInstanceOf(RuntimeException.class)
                    .hasMessageContaining("Statement not found");
        }
    }

    // ══════════════════════════════════════════════════════════════════════════
    //  Transaction field mapping (strVal / numVal edge cases)
    // ══════════════════════════════════════════════════════════════════════════

    @Nested
    @DisplayName("Transaction field mapping")
    class TransactionMappingTests {

        @BeforeEach
        void setupFile() throws Exception {
            when(mockFile.getOriginalFilename()).thenReturn("test.pdf");
            when(mockFile.getBytes()).thenReturn(new byte[]{1});
        }

        @Test
        @DisplayName("null fields in transaction map produce null fields in saved Transaction")
        void nullFieldsProduceNullTransactionFields() throws Exception {
            Map<String, Object> txn = new HashMap<>();
            txn.put("Date", null); txn.put("Description", null);
            txn.put("Debit", null); txn.put("Credit", null);
            txn.put("Balance", null); txn.put("Reference", null); txn.put("Category", null);
            stubSingleTransactionResponse(txn);

            service.uploadAndParse(mockFile, buildMeta("X", "Y"));

            Transaction saved = capturedTransaction();
            assertThat(saved.getDate()).isNull();
            assertThat(saved.getDebit()).isNull();
            assertThat(saved.getBalance()).isNull();
        }

        @Test
        @DisplayName("'None' string values are normalised to null")
        void noneStringIsNull() throws Exception {
            Map<String, Object> txn = txnWith("None", "None", null, 500.0, 1000.0, "REF", "None");
            stubSingleTransactionResponse(txn);

            service.uploadAndParse(mockFile, buildMeta("X", "Y"));

            Transaction saved = capturedTransaction();
            assertThat(saved.getDate()).isNull();
            assertThat(saved.getDescription()).isNull();
            assertThat(saved.getCategory()).isNull();
        }

        @Test
        @DisplayName("'NaT' string for date is normalised to null")
        void natStringIsNull() throws Exception {
            Map<String, Object> txn = txnWith("NaT", "Purchase", 200.0, null, 800.0, "REF", "Food");
            stubSingleTransactionResponse(txn);

            service.uploadAndParse(mockFile, buildMeta("X", "Y"));

            assertThat(capturedTransaction().getDate()).isNull();
        }

        @Test
        @DisplayName("numeric strings are correctly parsed into Double values")
        void numericStringsAreParsed() throws Exception {
            Map<String, Object> txn = txnWith("2025-01-01", "ATM", "2500.75", null, "10000.00", null, "ATM");
            stubSingleTransactionResponse(txn);

            service.uploadAndParse(mockFile, buildMeta("X", "Y"));

            Transaction saved = capturedTransaction();
            assertThat(saved.getDebit()).isEqualTo(2500.75);
            assertThat(saved.getBalance()).isEqualTo(10000.00);
        }

        @Test
        @DisplayName("row indices are assigned sequentially starting from 0")
        void rowIndicesAssigned() throws Exception {
            String json = successParserResponse(3);
            when(restTemplate.postForEntity(anyString(), any(), eq(String.class)))
                    .thenReturn(new ResponseEntity<>(json, HttpStatus.OK));
            when(statementRepo.save(any())).thenAnswer(inv -> withId(inv.getArgument(0), 1L));

            service.uploadAndParse(mockFile, buildMeta("X", "Y"));

            ArgumentCaptor<List> captor = ArgumentCaptor.forClass(List.class);
            verify(transactionRepo).saveAll(captor.capture());
            List<Transaction> saved = captor.getValue();
            assertThat(saved.get(0).getRowIndex()).isEqualTo(0);
            assertThat(saved.get(1).getRowIndex()).isEqualTo(1);
            assertThat(saved.get(2).getRowIndex()).isEqualTo(2);
        }

        @Test
        @DisplayName("existing transactions are deleted before saving new ones")
        void existingTransactionsDeletedFirst() throws Exception {
            String json = successParserResponse(2);
            when(restTemplate.postForEntity(anyString(), any(), eq(String.class)))
                    .thenReturn(new ResponseEntity<>(json, HttpStatus.OK));
            when(statementRepo.save(any())).thenAnswer(inv -> withId(inv.getArgument(0), 5L));

            service.uploadAndParse(mockFile, buildMeta("X", "Y"));

            verify(transactionRepo).deleteByStatementId(5L);
        }

        @Test
        @DisplayName("totalTransactions is updated to the actual saved count")
        void totalTransactionsUpdated() throws Exception {
            String json = successParserResponse(4);
            when(restTemplate.postForEntity(anyString(), any(), eq(String.class)))
                    .thenReturn(new ResponseEntity<>(json, HttpStatus.OK));
            when(statementRepo.save(any())).thenAnswer(inv -> withId(inv.getArgument(0), 1L));

            Statement result = service.uploadAndParse(mockFile, buildMeta("X", "Y"));
            assertThat(result.getTotalTransactions()).isEqualTo(4);
        }

        // ── helpers ───────────────────────────────────────────────────────────

        private Map<String, Object> txnWith(Object date, Object desc, Object debit,
                                             Object credit, Object balance,
                                             Object ref, Object cat) {
            Map<String, Object> t = new HashMap<>();
            t.put("Date", date); t.put("Description", desc);
            t.put("Debit", debit); t.put("Credit", credit);
            t.put("Balance", balance); t.put("Reference", ref); t.put("Category", cat);
            return t;
        }

        private void stubSingleTransactionResponse(Map<String, Object> txn) throws Exception {
            Map<String, Object> meta = Map.of("bank", "SBI", "engine", "test",
                    "total_rows", 1, "balance_mismatches", 0,
                    "confidence", 1.0, "debit_total", 0.0, "credit_total", 0.0);
            Map<String, Object> resp = new HashMap<>();
            resp.put("status", "success");
            resp.put("meta", meta);
            resp.put("transactions", List.of(txn));
            String json = objectMapper.writeValueAsString(resp);
            when(restTemplate.postForEntity(anyString(), any(), eq(String.class)))
                    .thenReturn(new ResponseEntity<>(json, HttpStatus.OK));
            when(statementRepo.save(any())).thenAnswer(inv -> withId(inv.getArgument(0), 1L));
        }

        @SuppressWarnings("unchecked")
        private Transaction capturedTransaction() {
            ArgumentCaptor<List> captor = ArgumentCaptor.forClass(List.class);
            verify(transactionRepo).saveAll(captor.capture());
            return (Transaction) captor.getValue().get(0);
        }
    }

    // ── shared utility ────────────────────────────────────────────────────────

    private Statement withId(Statement s, Long id) {
        s.setId(id);
        return s;
    }
}
