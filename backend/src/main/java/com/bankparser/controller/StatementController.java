package com.bankparser.controller;

import com.bankparser.dto.StatementUploadRequest;
import com.bankparser.model.Statement;
import com.bankparser.model.Transaction;
import com.bankparser.service.StatementService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVPrinter;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.logging.Logger;

@RestController
@RequestMapping("/api/statements")
public class StatementController {

    private static final Logger log = Logger.getLogger(StatementController.class.getName());
    private final StatementService service;
    private final ObjectMapper objectMapper;

    public StatementController(StatementService service, ObjectMapper objectMapper) {
        this.service = service;
        this.objectMapper = objectMapper;
    }

    @GetMapping
    public ResponseEntity<List<Statement>> list(
            @RequestParam(name = "scope", defaultValue = "mine") String scope) {
        return ResponseEntity.ok(service.getStatements(scope));
    }

    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<?> upload(
            @RequestPart("file") MultipartFile file,
            @RequestPart("metadata") String metadataJson) {
        try {
            StatementUploadRequest meta = objectMapper.readValue(metadataJson, StatementUploadRequest.class);
            Statement stmt = service.uploadAndParse(file, meta);
            return ResponseEntity.ok(stmt);
        } catch (Exception e) {
            log.severe("Upload failed: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("error", e.getMessage()));
        }
    }

    @GetMapping("/{id}")
    public ResponseEntity<?> get(@PathVariable Long id) {
        return service.getStatement(id)
                .<ResponseEntity<?>>map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/{id}/unlock")
    public ResponseEntity<?> unlock(@PathVariable Long id, @RequestBody Map<String, String> body) {
        try {
            Statement stmt = service.unlockWithPassword(id, body.getOrDefault("password", ""));
            return ResponseEntity.ok(stmt);
        } catch (Exception e) {
            log.severe("Unlock failed id=" + id + ": " + e.getMessage());
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of("error", e.getMessage()));
        }
    }

    @GetMapping("/{id}/transactions")
    public ResponseEntity<List<Transaction>> transactions(@PathVariable Long id) {
        return ResponseEntity.ok(service.getTransactions(id));
    }

    @GetMapping("/{id}/insights")
    public ResponseEntity<?> insights(@PathVariable Long id) {
        try {
            return ResponseEntity.ok(service.getInsights(id));
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(Map.of("error", e.getMessage()));
        }
    }

    @GetMapping("/{id}/scorecard")
    public ResponseEntity<?> scorecard(@PathVariable Long id) {
        try {
            return ResponseEntity.ok(service.getScorecard(id));
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(Map.of("error", e.getMessage()));
        }
    }

    @GetMapping("/{id}/export/csv")
    public ResponseEntity<byte[]> exportCsv(@PathVariable Long id) {
        try {
            List<Transaction> txns = service.getTransactions(id);
            Statement stmt = service.getStatement(id).orElseThrow();
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            CSVPrinter printer = new CSVPrinter(
                    new OutputStreamWriter(baos, StandardCharsets.UTF_8),
                    CSVFormat.DEFAULT.builder()
                            .setHeader("Date","Description","Category","Debit (Rs)","Credit (Rs)","Balance (Rs)","Reference")
                            .build()
            );
            for (Transaction t : txns) {
                printer.printRecord(
                        t.getDate(), t.getDescription(), t.getCategory(),
                        t.getDebit()   != null ? String.format("%.2f", t.getDebit())   : "",
                        t.getCredit()  != null ? String.format("%.2f", t.getCredit())  : "",
                        t.getBalance() != null ? String.format("%.2f", t.getBalance()) : "",
                        t.getReference()
                );
            }
            printer.flush();
            String name = stmt.getCustomerName() != null ? stmt.getCustomerName().replaceAll("\\s+", "_") : "export";
            return ResponseEntity.ok()
                    .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"statement_" + id + "_" + name + ".csv\"")
                    .contentType(MediaType.parseMediaType("text/csv"))
                    .body(baos.toByteArray());
        } catch (Exception e) {
            log.severe("CSV export failed: " + e.getMessage());
            return ResponseEntity.internalServerError().build();
        }
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        service.deleteStatement(id);
        return ResponseEntity.noContent().build();
    }
}
