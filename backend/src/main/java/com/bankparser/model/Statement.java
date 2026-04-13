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

    @Column(columnDefinition = "TEXT")
    private String customerName;

    @Column(columnDefinition = "TEXT")
    private String bankName;

    @Column(columnDefinition = "TEXT")
    private String accountNumber;

    @Column(columnDefinition = "TEXT")
    private String statementPeriod;

    @Column(columnDefinition = "TEXT")
    private String analystName;

    @Column(columnDefinition = "TEXT")
    private String notes;

    @Column(columnDefinition = "TEXT")
    private String originalFileName;

    @Column(columnDefinition = "TEXT")
    private String fileKey;

    @Column(length = 20)
    private String fileType;          // PDF / XLSX / XLS / ODS / CSV

    @Column(length = 50)
    private String status;

    @Column(columnDefinition = "TEXT")
    private String detectedBank;

    @Column(columnDefinition = "TEXT")
    private String engineUsed;
    private Double confidence;
    private Integer totalTransactions;
    private Integer balanceMismatches;
    private Double debitTotal;
    private Double creditTotal;
    @Column(columnDefinition = "TEXT")
    private String errorMessage;

    // Analytics stored as JSON strings (avoids extra tables for MVP)
    @Column(columnDefinition = "TEXT")
    private String insightsJson;

    @Column(columnDefinition = "TEXT")
    private String scorecardJson;

    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

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
    public String getFileType()           { return fileType; }
    public String getStatus()             { return status; }
    public String getDetectedBank()       { return detectedBank; }
    public String getEngineUsed()         { return engineUsed; }
    public Double getConfidence()         { return confidence; }
    public Integer getTotalTransactions() { return totalTransactions; }
    public Integer getBalanceMismatches() { return balanceMismatches; }
    public Double getDebitTotal()         { return debitTotal; }
    public Double getCreditTotal()        { return creditTotal; }
    public String getErrorMessage()       { return errorMessage; }
    public String getInsightsJson()       { return insightsJson; }
    public String getScorecardJson()      { return scorecardJson; }
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
    public void setFileType(String v)            { this.fileType = v; }
    public void setStatus(String v)              { this.status = v; }
    public void setDetectedBank(String v)        { this.detectedBank = v; }
    public void setEngineUsed(String v)          { this.engineUsed = v; }
    public void setConfidence(Double v)          { this.confidence = v; }
    public void setTotalTransactions(Integer v)  { this.totalTransactions = v; }
    public void setBalanceMismatches(Integer v)  { this.balanceMismatches = v; }
    public void setDebitTotal(Double v)          { this.debitTotal = v; }
    public void setCreditTotal(Double v)         { this.creditTotal = v; }
    public void setErrorMessage(String v)        { this.errorMessage = v; }
    public void setInsightsJson(String v)        { this.insightsJson = v; }
    public void setScorecardJson(String v)       { this.scorecardJson = v; }
    public void setCreatedAt(LocalDateTime v)    { this.createdAt = v; }
    public void setUpdatedAt(LocalDateTime v)    { this.updatedAt = v; }
    public void setTransactions(List<Transaction> v) { this.transactions = v; }
}
