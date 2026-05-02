package com.bankparser.model;

import jakarta.persistence.*;
import com.fasterxml.jackson.annotation.JsonBackReference;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Objects;

@Entity
@Table(
    name = "transactions",
    indexes = {
        @Index(name = "idx_transaction_date", columnList = "transaction_date"),
        @Index(name = "idx_transaction_category", columnList = "category"),
        @Index(name = "idx_transaction_reference", columnList = "reference")
    }
)
public class Transaction {

    // ── Constants ─────────────────────────────────────────────────────────────
    public static final String TYPE_DEBIT = "DEBIT";
    public static final String TYPE_CREDIT = "CREDIT";

    // ── Primary Key ───────────────────────────────────────────────────────────
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // ── Relationships ─────────────────────────────────────────────────────────
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "statement_id", nullable = false)
    @JsonBackReference
    private Statement statement;

    // ── Core Fields ───────────────────────────────────────────────────────────
    @Column(name = "transaction_date", nullable = false)
    private LocalDate date;

    @Column(length = 1000, nullable = false)
    private String description;

    // BigDecimal is preferred over Double for financial precision
    @Column(precision = 15, scale = 2)
    private BigDecimal debit;

    @Column(precision = 15, scale = 2)
    private BigDecimal credit;

    @Column(precision = 15, scale = 2)
    private BigDecimal balance;

    @Column(length = 500, unique = false)
    private String reference;

    private Integer rowIndex;

    // Rule-based or ML categorization
    @Column(length = 100)
    private String category;

    // Transaction type: DEBIT / CREDIT
    @Column(length = 20)
    private String transactionType;

    // Merchant / vendor extraction
    @Column(length = 255)
    private String merchantName;

    // User notes
    @Column(length = 1000)
    private String notes;

    // Fraud or anomaly detection marker
    private Boolean flagged = false;

    // ── Lifecycle Hooks ───────────────────────────────────────────────────────
    @PrePersist
    @PreUpdate
    private void autoDetectTransactionType() {
        if (debit != null && debit.compareTo(BigDecimal.ZERO) > 0) {
            this.transactionType = TYPE_DEBIT;
        } else if (credit != null && credit.compareTo(BigDecimal.ZERO) > 0) {
            this.transactionType = TYPE_CREDIT;
        }
    }

    // ── Business Methods ──────────────────────────────────────────────────────
    public BigDecimal getTransactionAmount() {
        if (debit != null) return debit;
        if (credit != null) return credit;
        return BigDecimal.ZERO;
    }

    public boolean isDebitTransaction() {
        return TYPE_DEBIT.equalsIgnoreCase(transactionType);
    }

    public boolean isCreditTransaction() {
        return TYPE_CREDIT.equalsIgnoreCase(transactionType);
    }

    // ── Getters ───────────────────────────────────────────────────────────────
    public Long getId() { return id; }
    public Statement getStatement() { return statement; }
    public LocalDate getDate() { return date; }
    public String getDescription() { return description; }
    public BigDecimal getDebit() { return debit; }
    public BigDecimal getCredit() { return credit; }
    public BigDecimal getBalance() { return balance; }
    public String getReference() { return reference; }
    public Integer getRowIndex() { return rowIndex; }
    public String getCategory() { return category; }
    public String getTransactionType() { return transactionType; }
    public String getMerchantName() { return merchantName; }
    public String getNotes() { return notes; }
    public Boolean getFlagged() { return flagged; }

    // ── Setters ───────────────────────────────────────────────────────────────
    public void setId(Long id) { this.id = id; }
    public void setStatement(Statement statement) { this.statement = statement; }
    public void setDate(LocalDate date) { this.date = date; }
    public void setDescription(String description) { this.description = description; }
    public void setDebit(BigDecimal debit) { this.debit = debit; }
    public void setCredit(BigDecimal credit) { this.credit = credit; }
    public void setBalance(BigDecimal balance) { this.balance = balance; }
    public void setReference(String reference) { this.reference = reference; }
    public void setRowIndex(Integer rowIndex) { this.rowIndex = rowIndex; }
    public void setCategory(String category) { this.category = category; }
    public void setTransactionType(String transactionType) { this.transactionType = transactionType; }
    public void setMerchantName(String merchantName) { this.merchantName = merchantName; }
    public void setNotes(String notes) { this.notes = notes; }
    public void setFlagged(Boolean flagged) { this.flagged = flagged; }

    // ── Equality ──────────────────────────────────────────────────────────────
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof Transaction)) return false;
        Transaction that = (Transaction) o;
        return Objects.equals(id, that.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }

    // ── Debugging ─────────────────────────────────────────────────────────────
    @Override
    public String toString() {
        return "Transaction{" +
                "id=" + id +
                ", date=" + date +
                ", description='" + description + '\'' +
                ", debit=" + debit +
                ", credit=" + credit +
                ", balance=" + balance +
                ", category='" + category + '\'' +
                ", transactionType='" + transactionType + '\'' +
                ", merchantName='" + merchantName + '\'' +
                ", flagged=" + flagged +
                '}';
    }
}