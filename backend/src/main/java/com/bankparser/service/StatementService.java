package com.bankparser.service;

import com.bankparser.dto.StatementUploadRequest;
import com.bankparser.model.Statement;
import com.bankparser.model.Transaction;
import com.bankparser.repository.StatementRepository;
import com.bankparser.repository.TransactionRepository;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.logging.Logger;

@Service
public class StatementService {

    private static final Logger log = Logger.getLogger(StatementService.class.getName());

    private final StatementRepository statementRepo;
    private final TransactionRepository transactionRepo;
    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    @Value("${parser.service.url:http://localhost:5050}")
    private String parserUrl;

    public StatementService(StatementRepository statementRepo,
                            TransactionRepository transactionRepo,
                            RestTemplate restTemplate,
                            ObjectMapper objectMapper) {
        this.statementRepo   = statementRepo;
        this.transactionRepo = transactionRepo;
        this.restTemplate    = restTemplate;
        this.objectMapper    = objectMapper;
    }

    // ── Upload & first parse ──────────────────────────────────────────────────
    public Statement uploadAndParse(MultipartFile file, StatementUploadRequest meta) throws Exception {
        Statement stmt = new Statement();
        stmt.setCustomerName(meta.getCustomerName());
        stmt.setBankName(meta.getBankName());
        stmt.setAccountNumber(meta.getAccountNumber());
        stmt.setStatementPeriod(meta.getStatementPeriod());
        stmt.setAnalystName(meta.getAnalystName());
        stmt.setNotes(meta.getNotes());
        stmt.setOriginalFileName(file.getOriginalFilename());
        stmt.setStatus("PROCESSING");
        stmt = statementRepo.save(stmt);

        try {
            Map<String, Object> result = callParser(file, null, null);
            applyParserResult(stmt, result);
        } catch (Exception e) {
            log.severe("Parser call failed: " + e.getMessage());
            stmt.setStatus("ERROR");
            stmt.setErrorMessage("Parser error: " + e.getMessage());
        }
        return statementRepo.save(stmt);
    }

    // ── Retry with password ───────────────────────────────────────────────────
    public Statement unlockWithPassword(Long statementId, String password) throws Exception {
        Statement stmt = statementRepo.findById(statementId)
                .orElseThrow(() -> new RuntimeException("Statement not found: " + statementId));

        if (!"PENDING_PASSWORD".equals(stmt.getStatus())) {
            throw new RuntimeException("Statement is not waiting for a password.");
        }

        try {
            Map<String, Object> result = callParser(null, stmt.getFileKey(), password);
            applyParserResult(stmt, result);
        } catch (Exception e) {
            log.severe("Unlock failed: " + e.getMessage());
            stmt.setStatus("PENDING_PASSWORD");
            stmt.setErrorMessage("Wrong password or parser error: " + e.getMessage());
        }
        return statementRepo.save(stmt);
    }

    // ── Queries ───────────────────────────────────────────────────────────────
    public List<Statement> getAllStatements() {
        return statementRepo.findAllByOrderByCreatedAtDesc();
    }

    public Optional<Statement> getStatement(Long id) {
        return statementRepo.findById(id);
    }

    public List<Transaction> getTransactions(Long statementId) {
        return transactionRepo.findByStatementIdOrderByRowIndex(statementId);
    }

    public void deleteStatement(Long id) {
        transactionRepo.deleteByStatementId(id);
        statementRepo.deleteById(id);
    }

    // ── Core: call Python service, get response as String then parse ──────────
    // Using String.class avoids RestTemplate deserialization errors completely.
    // We parse manually with Jackson so we see exactly what Python returned.
    private Map<String, Object> callParser(
            MultipartFile file, String fileKey, String password) throws Exception {

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();

        if (file != null) {
            final String fileName = file.getOriginalFilename();
            byte[] bytes = file.getBytes();
            ByteArrayResource resource = new ByteArrayResource(bytes) {
                @Override public String getFilename() { return fileName; }
            };
            body.add("file", resource);
            log.info("Sending file to parser: " + fileName + " (" + bytes.length + " bytes)");
        }
        if (fileKey != null && !fileKey.isBlank()) {
            body.add("file_key", fileKey);
            log.info("Sending file_key: " + fileKey);
        }
        if (password != null && !password.isBlank()) {
            body.add("password", password);
            log.info("Sending password (masked)");
        }

        HttpEntity<MultiValueMap<String, Object>> request = new HttpEntity<>(body, headers);

        String rawResponse;
        try {
            // Get raw string — never fails on content-type mismatch
            ResponseEntity<String> response = restTemplate.postForEntity(
                    parserUrl + "/parse", request, String.class
            );
            rawResponse = response.getBody();
            log.info("Parser HTTP status: " + response.getStatusCode());
        } catch (HttpStatusCodeException e) {
            // 4xx / 5xx — body still contains useful info
            rawResponse = e.getResponseBodyAsString();
            log.severe("Parser returned HTTP error " + e.getStatusCode() + ": " + rawResponse);
        }

        log.info("Parser raw response: " + (rawResponse != null ? rawResponse.substring(0, Math.min(200, rawResponse.length())) : "null"));

        if (rawResponse == null || rawResponse.isBlank()) {
            throw new RuntimeException("Python parser returned empty response");
        }

        // Parse JSON
        try {
            return objectMapper.readValue(rawResponse, new TypeReference<Map<String, Object>>() {});
        } catch (Exception e) {
            throw new RuntimeException("Parser response is not valid JSON. Raw: " + rawResponse.substring(0, Math.min(300, rawResponse.length())));
        }
    }

    // ── Apply parser result to Statement ──────────────────────────────────────
    @SuppressWarnings("unchecked")
    private void applyParserResult(Statement stmt, Map<String, Object> result) {
        if (result == null) {
            stmt.setStatus("ERROR");
            stmt.setErrorMessage("Parser service returned no response.");
            return;
        }

        String status = (String) result.getOrDefault("status", "error");
        Object fileKeyObj = result.get("file_key");
        if (fileKeyObj != null) stmt.setFileKey(fileKeyObj.toString());

        log.info("Parser status: " + status);

        switch (status) {
            case "success" -> {
                stmt.setStatus("DONE");
                Map<String, Object> meta = (Map<String, Object>) result.get("meta");
                if (meta != null) {
                    stmt.setDetectedBank(strVal(meta.get("bank")));
                    stmt.setEngineUsed(strVal(meta.get("engine")));
                    Object tr = meta.get("total_rows");
                    if (tr instanceof Number n) stmt.setTotalTransactions(n.intValue());
                    Object bm = meta.get("balance_mismatches");
                    if (bm instanceof Number n) stmt.setBalanceMismatches(n.intValue());
                    Object conf = meta.get("confidence");
                    if (conf instanceof Number n) stmt.setConfidence(n.doubleValue());
                    Object dt = meta.get("debit_total");
                    if (dt instanceof Number n) stmt.setDebitTotal(n.doubleValue());
                    Object ct = meta.get("credit_total");
                    if (ct instanceof Number n) stmt.setCreditTotal(n.doubleValue());
                }
                List<Map<String, Object>> txns = (List<Map<String, Object>>) result.get("transactions");
                saveTransactions(stmt, txns);
            }
            case "password_required" -> {
                stmt.setStatus("PENDING_PASSWORD");
                log.info("PDF requires password");
            }
            case "wrong_password" -> {
                stmt.setStatus("PENDING_PASSWORD");
                stmt.setErrorMessage("Wrong password.");
            }
            default -> {
                stmt.setStatus("ERROR");
                stmt.setErrorMessage(strVal(result.getOrDefault("message", "Unknown parser error: " + status)));
            }
        }
    }

    private void saveTransactions(Statement stmt, List<Map<String, Object>> txns) {
        if (txns == null) {
            log.warning("No transactions list in parser response");
            return;
        }
        transactionRepo.deleteByStatementId(stmt.getId());

        List<Transaction> list = new ArrayList<>();
        for (int i = 0; i < txns.size(); i++) {
            Map<String, Object> t = txns.get(i);
            Transaction tx = new Transaction();
            tx.setStatement(stmt);
            tx.setRowIndex(i);
            tx.setDate(strVal(t.get("Date")));
            tx.setDescription(strVal(t.get("Description")));
            tx.setDebit(numVal(t.get("Debit")));
            tx.setCredit(numVal(t.get("Credit")));
            tx.setBalance(numVal(t.get("Balance")));
            tx.setReference(strVal(t.get("Reference")));
            list.add(tx);
        }
        transactionRepo.saveAll(list);
        stmt.setTotalTransactions(list.size());
        log.info("Saved " + list.size() + " transactions for statement " + stmt.getId());
    }

    private String strVal(Object v) {
        if (v == null) return null;
        String s = v.toString().trim();
        return (s.isEmpty() || s.equals("None") || s.equals("NaT") || s.equals("null")) ? null : s;
    }

    private Double numVal(Object v) {
        if (v == null) return null;
        try { return Double.parseDouble(v.toString()); }
        catch (Exception e) { return null; }
    }
}
