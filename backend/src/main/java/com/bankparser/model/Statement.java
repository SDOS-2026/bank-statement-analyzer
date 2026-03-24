package com.bankparser.model;

import jakarta.persistence.*;
import com.fasterxml.jackson.annotation.JsonIgnore;
import java.time.LocalDateTime;
import java.util.List;

@Entity
@Table(name = "statements")
public class Statement {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String customerName;
    private String bankName;
    private String accountNumber;
    private String statementPeriod;
    private String analystName;
    private String notes;
    private String originalFileName;
    private String fileKey;
    private String status;
    private String detectedBank;
    private String engineUsed;
    private Double confidence;
    private Integer totalTransactions;
    private Integer balanceMismatches;
    private Double debitTotal;
    private Double creditTotal;
    private String errorMessage;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    // @JsonIgnore prevents Jackson from trying to lazily load this
    // collection during HTTP response serialization (outside transaction)
    @JsonIgnore
    @OneToMany(mappedBy = "statement", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<Transaction> transactions;

    @PrePersist
    protected void onCreate() { createdAt = LocalDateTime.now(); updatedAt = LocalDateTime.now(); }
    @PreUpdate
    protected void onUpdate() { updatedAt = LocalDateTime.now(); }

    // ── Getters ───────────────────────────────────────────────────────────────
    public Long getId()                   { return id; }
    public String getCustomerName()       { return customerName; }
    public String getBankName()           { return bankName; }
    public String getAccountNumber()      { return accountNumber; }
    public String getStatementPeriod()    { return statementPeriod; }
    public String getAnalystName()        { return analystName; }
    public String getNotes()              { return notes; }
    public String getOriginalFileName()   { return originalFileName; }
    public String getFileKey()            { return fileKey; }
    public String getStatus()             { return status; }
    public String getDetectedBank()       { return detectedBank; }
    public String getEngineUsed()         { return engineUsed; }
    public Double getConfidence()         { return confidence; }
    public Integer getTotalTransactions() { return totalTransactions; }
    public Integer getBalanceMismatches() { return balanceMismatches; }
    public Double getDebitTotal()         { return debitTotal; }
    public Double getCreditTotal()        { return creditTotal; }
    public String getErrorMessage()       { return errorMessage; }
    public LocalDateTime getCreatedAt()   { return createdAt; }
    public LocalDateTime getUpdatedAt()   { return updatedAt; }
    public List<Transaction> getTransactions() { return transactions; }

    // ── Setters ───────────────────────────────────────────────────────────────
    public void setId(Long v)                    { this.id = v; }
    public void setCustomerName(String v)        { this.customerName = v; }
    public void setBankName(String v)            { this.bankName = v; }
    public void setAccountNumber(String v)       { this.accountNumber = v; }
    public void setStatementPeriod(String v)     { this.statementPeriod = v; }
    public void setAnalystName(String v)         { this.analystName = v; }
    public void setNotes(String v)               { this.notes = v; }
    public void setOriginalFileName(String v)    { this.originalFileName = v; }
    public void setFileKey(String v)             { this.fileKey = v; }
    public void setStatus(String v)              { this.status = v; }
    public void setDetectedBank(String v)        { this.detectedBank = v; }
    public void setEngineUsed(String v)          { this.engineUsed = v; }
    public void setConfidence(Double v)          { this.confidence = v; }
    public void setTotalTransactions(Integer v)  { this.totalTransactions = v; }
    public void setBalanceMismatches(Integer v)  { this.balanceMismatches = v; }
    public void setDebitTotal(Double v)          { this.debitTotal = v; }
    public void setCreditTotal(Double v)         { this.creditTotal = v; }
    public void setErrorMessage(String v)        { this.errorMessage = v; }
    public void setCreatedAt(LocalDateTime v)    { this.createdAt = v; }
    public void setUpdatedAt(LocalDateTime v)    { this.updatedAt = v; }
    public void setTransactions(List<Transaction> v) { this.transactions = v; }
}
