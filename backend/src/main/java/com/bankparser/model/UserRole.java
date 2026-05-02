package com.bankparser.model;

public enum UserRole {
    USER,
    INTERNAL;

    public boolean isInternal() {
        return this == INTERNAL;
    }
}
