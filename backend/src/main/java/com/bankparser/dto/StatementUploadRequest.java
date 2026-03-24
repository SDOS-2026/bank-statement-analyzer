package com.bankparser.dto;

public class StatementUploadRequest {
    private String customerName;
    private String bankName;
    private String accountNumber;
    private String statementPeriod;
    private String analystName;
    private String notes;

    public String getCustomerName()    { return customerName; }
    public String getBankName()        { return bankName; }
    public String getAccountNumber()   { return accountNumber; }
    public String getStatementPeriod() { return statementPeriod; }
    public String getAnalystName()     { return analystName; }
    public String getNotes()           { return notes; }

    public void setCustomerName(String v)    { this.customerName = v; }
    public void setBankName(String v)        { this.bankName = v; }
    public void setAccountNumber(String v)   { this.accountNumber = v; }
    public void setStatementPeriod(String v) { this.statementPeriod = v; }
    public void setAnalystName(String v)     { this.analystName = v; }
    public void setNotes(String v)           { this.notes = v; }
}
