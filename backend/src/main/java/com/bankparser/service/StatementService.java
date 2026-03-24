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

    }

    // ── Retry with password ───────────────────────────────────────────────────
    public Statement unlockWithPassword(Long statementId, String password) throws Exception {

    }

    // ── Queries ───────────────────────────────────────────────────────────────
    public List<Statement> getAllStatements() {

    }

    public Optional<Statement> getStatement(Long id) {

    }

    public List<Transaction> getTransactions(Long statementId) {

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

    }

    // ── Apply parser result to Statement ──────────────────────────────────────
    @SuppressWarnings("unchecked")
    private void applyParserResult(Statement stmt, Map<String, Object> result) {
        
    }

    private void saveTransactions(Statement stmt, List<Map<String, Object>> txns) {
    }

    private String strVal(Object v) {
       
    }

    private Double numVal(Object v) {
        if (v == null) return null;
        try { return Double.parseDouble(v.toString()); }
        catch (Exception e) { return null; }
    }
}
