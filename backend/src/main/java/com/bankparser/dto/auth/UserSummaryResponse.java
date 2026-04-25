package com.bankparser.dto.auth;

import com.bankparser.model.AppUser;

public class UserSummaryResponse {
    private Long id;
    private String email;
    private String fullName;
    private String role;

    public static UserSummaryResponse from(AppUser user) {
        UserSummaryResponse response = new UserSummaryResponse();
        response.setId(user.getId());
        response.setEmail(user.getEmail());
        response.setFullName(user.getFullName());
        response.setRole(user.getRole().name());
        return response;
    }

    public Long getId() { return id; }
    public String getEmail() { return email; }
    public String getFullName() { return fullName; }
    public String getRole() { return role; }
    public void setId(Long id) { this.id = id; }
    public void setEmail(String email) { this.email = email; }
    public void setFullName(String fullName) { this.fullName = fullName; }
    public void setRole(String role) { this.role = role; }
}
