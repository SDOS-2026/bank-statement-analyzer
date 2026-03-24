package com.bankparser.controller;

import com.bankparser.dto.StatementUploadRequest;
import com.bankparser.model.Statement;
import com.bankparser.model.Transaction;
import com.bankparser.service.StatementService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVPrinter;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.ByteArrayOutputStream;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
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
    public ResponseEntity<List<Statement>> list() {
        return ResponseEntity.ok(service.getAllStatements());
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
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/{id}/unlock")
    public ResponseEntity<?> unlock(
            @PathVariable Long id,
            @RequestBody Map<String, String> body) {
        try {
            String password = body.getOrDefault("password", "");
            Statement stmt = service.unlockWithPassword(id, password);
            return ResponseEntity.ok(stmt);
        } catch (Exception e) {
            log.severe("Unlock failed for id=" + id + ": " + e.getMessage());
            return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                    .body(Map.of("error", e.getMessage()));
        }
    }

    @GetMapping("/{id}/transactions")
    public ResponseEntity<List<Transaction>> transactions(@PathVariable Long id) {
        return ResponseEntity.ok(service.getTransactions(id));
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
                            .setHeader("Date", "Description", "Debit (Rs)", "Credit (Rs)", "Balance (Rs)", "Reference")
                            .build()
            );

            for (Transaction t : txns) {
                printer.printRecord(
                        t.getDate(),
                        t.getDescription(),
                        t.getDebit()   != null ? String.format("%.2f", t.getDebit())   : "",
                        t.getCredit()  != null ? String.format("%.2f", t.getCredit())  : "",
                        t.getBalance() != null ? String.format("%.2f", t.getBalance()) : "",
                        t.getReference()
                );
            }
            printer.flush();

            String customerName = stmt.getCustomerName();
            String safeName = (customerName != null ? customerName.replaceAll("\\s+", "_") : "export");
            String filename = "statement_" + id + "_" + safeName + ".csv";

            return ResponseEntity.ok()
                    .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + filename + "\"")
                    .contentType(MediaType.parseMediaType("text/csv"))
                    .body(baos.toByteArray());

        } catch (Exception e) {
            log.severe("CSV export failed for id=" + id + ": " + e.getMessage());
            return ResponseEntity.internalServerError().build();
        }
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        service.deleteStatement(id);
        return ResponseEntity.noContent().build();
    }
}
