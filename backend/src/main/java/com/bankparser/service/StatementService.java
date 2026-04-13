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

import java.util.*;
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

    public Statement uploadAndParse(MultipartFile file, StatementUploadRequest meta) throws Exception {
        Statement stmt = new Statement();
        stmt.setCustomerName(meta.getCustomerName());
        stmt.setBankName(meta.getBankName());
        stmt.setAccountNumber(meta.getAccountNumber());
        stmt.setStatementPeriod(meta.getStatementPeriod());
        stmt.setAnalystName(meta.getAnalystName());
        stmt.setNotes(meta.getNotes());
        stmt.setOriginalFileName(file.getOriginalFilename());
        // Detect file type from extension
        String fn = file.getOriginalFilename() != null ? file.getOriginalFilename().toLowerCase() : "";
        stmt.setFileType(fn.endsWith(".xlsx") ? "XLSX" : fn.endsWith(".xls") ? "XLS" :
                         fn.endsWith(".ods") ? "ODS" : fn.endsWith(".csv") ? "CSV" : "PDF");
        stmt.setStatus("PROCESSING");
        stmt = statementRepo.save(stmt);

        try {
            Map<String, Object> result = callParser(file, null, null, meta.getBankName());
            applyParserResult(stmt, result);
        } catch (Exception e) {
            log.severe("Parser call failed: " + e.getMessage());
            stmt.setStatus("ERROR");
            stmt.setErrorMessage("Parser error: " + e.getMessage());
        }
        return statementRepo.save(stmt);
    }

    public Statement unlockWithPassword(Long statementId, String password) throws Exception {
        Statement stmt = statementRepo.findById(statementId)
                .orElseThrow(() -> new RuntimeException("Statement not found: " + statementId));
        if (!"PENDING_PASSWORD".equals(stmt.getStatus()))
            throw new RuntimeException("Statement is not waiting for a password.");

        try {
            Map<String, Object> result = callParser(null, stmt.getFileKey(), password, stmt.getBankName());
            applyParserResult(stmt, result);
        } catch (Exception e) {
            log.severe("Unlock failed: " + e.getMessage());
            stmt.setStatus("PENDING_PASSWORD");
            stmt.setErrorMessage("Wrong password or error: " + e.getMessage());
        }
        return statementRepo.save(stmt);
    }

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

    // ── Get insights as parsed Map ────────────────────────────────────────────
    public Map<String, Object> getInsights(Long statementId) throws Exception {
        Statement stmt = statementRepo.findById(statementId)
                .orElseThrow(() -> new RuntimeException("Statement not found: " + statementId));
        String json = stmt.getInsightsJson();
        if (json == null || json.isBlank()) return Map.of();
        return objectMapper.readValue(json, new TypeReference<Map<String, Object>>() {});
    }

    public Map<String, Object> getScorecard(Long statementId) throws Exception {
        Statement stmt = statementRepo.findById(statementId)
                .orElseThrow(() -> new RuntimeException("Statement not found: " + statementId));
        String json = stmt.getScorecardJson();
        if (json == null || json.isBlank()) return Map.of();
        return objectMapper.readValue(json, new TypeReference<Map<String, Object>>() {});
    }

    // ── Internal ──────────────────────────────────────────────────────────────

    private Map<String, Object> callParser(
            MultipartFile file, String fileKey, String password, String bankName) throws Exception {

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
            log.info("Sending file: " + fileName + " (" + bytes.length + " bytes)");
        }
        if (fileKey != null && !fileKey.isBlank()) body.add("file_key", fileKey);
        if (password != null && !password.isBlank()) body.add("password", password);
        if (bankName != null && !bankName.isBlank()) body.add("bank_name", bankName);

        HttpEntity<MultiValueMap<String, Object>> request = new HttpEntity<>(body, headers);

        String rawResponse;
        try {
            ResponseEntity<String> response = restTemplate.postForEntity(
                    parserUrl + "/parse", request, String.class);
            rawResponse = response.getBody();
            log.info("Parser HTTP: " + response.getStatusCode());
        } catch (HttpStatusCodeException e) {
            rawResponse = e.getResponseBodyAsString();
            log.severe("Parser HTTP error " + e.getStatusCode() + ": " + rawResponse);
        }

        if (rawResponse == null || rawResponse.isBlank())
            throw new RuntimeException("Parser returned empty response");

        log.info("Parser response (first 200): " +
                rawResponse.substring(0, Math.min(200, rawResponse.length())));

        return objectMapper.readValue(rawResponse, new TypeReference<Map<String, Object>>() {});
    }

    @SuppressWarnings("unchecked")
    private void applyParserResult(Statement stmt, Map<String, Object> result) {
        if (result == null) { stmt.setStatus("ERROR"); stmt.setErrorMessage("No response"); return; }

        String status = (String) result.getOrDefault("status", "error");
        Object fk = result.get("file_key");
        if (fk != null) stmt.setFileKey(fk.toString());

        log.info("Parser status: " + status);

        switch (status) {
            case "success" -> {
                stmt.setStatus("DONE");
                stmt.setErrorMessage(null);
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
                // Store insights and scorecard as JSON
                try {
                    Object ins = result.get("insights");
                    if (ins != null) stmt.setInsightsJson(objectMapper.writeValueAsString(ins));
                    Object sc = result.get("scorecard");
                    if (sc != null) stmt.setScorecardJson(objectMapper.writeValueAsString(sc));
                } catch (Exception e) {
                    log.warning("Failed to serialize insights/scorecard: " + e.getMessage());
                }
                List<Map<String, Object>> txns = (List<Map<String, Object>>) result.get("transactions");
                saveTransactions(stmt, txns);
            }
            case "password_required" -> {
                stmt.setStatus("PENDING_PASSWORD");
                stmt.setErrorMessage(null);
            }
            case "wrong_password"    -> { stmt.setStatus("PENDING_PASSWORD"); stmt.setErrorMessage("Wrong password."); }
            default -> { stmt.setStatus("ERROR"); stmt.setErrorMessage(strVal(result.getOrDefault("message", "Unknown error: " + status))); }
        }
    }

    private void saveTransactions(Statement stmt, List<Map<String, Object>> txns) {
        if (txns == null) return;
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
            tx.setCategory(strVal(t.get("Category")));
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
        try { return Double.parseDouble(v.toString()); } catch (Exception e) { return null; }
    }
}
