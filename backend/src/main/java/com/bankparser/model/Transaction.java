package com.bankparser.model;

import jakarta.persistence.*;
import com.fasterxml.jackson.annotation.JsonBackReference;

@Entity
@Table(name = "transactions")
public class Transaction {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "statement_id")
    @JsonBackReference
    private Statement statement;

    private String date;

    @Column(length = 1000)
    private String description;

    private Double debit;
    private Double credit;
    private Double balance;

    @Column(length = 500)
    private String reference;

    private Integer rowIndex;

    // ── Getters ──────────────────────────────────────────────────────────────
    public Long getId()           { return id; }
    public Statement getStatement(){ return statement; }
    public String getDate()       { return date; }
    public String getDescription(){ return description; }
    public Double getDebit()      { return debit; }
    public Double getCredit()     { return credit; }
    public Double getBalance()    { return balance; }
    public String getReference()  { return reference; }
    public Integer getRowIndex()  { return rowIndex; }

    // ── Setters ──────────────────────────────────────────────────────────────
    public void setId(Long v)              { this.id = v; }
    public void setStatement(Statement v)  { this.statement = v; }
    public void setDate(String v)          { this.date = v; }
    public void setDescription(String v)   { this.description = v; }
    public void setDebit(Double v)         { this.debit = v; }
    public void setCredit(Double v)        { this.credit = v; }
    public void setBalance(Double v)       { this.balance = v; }
    public void setReference(String v)     { this.reference = v; }
    public void setRowIndex(Integer v)     { this.rowIndex = v; }
}
