package com.bankparser.service;

import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.logging.Logger;

@Service
public class BootstrapService {

    private static final Logger log = Logger.getLogger(BootstrapService.class.getName());

    private final AppUserService appUserService;

    @Value("${app.bootstrap.internal-email:}")
    private String internalEmail;

    @Value("${app.bootstrap.internal-password:}")
    private String internalPassword;

    @Value("${app.bootstrap.internal-name:FinParse Internal Admin}")
    private String internalName;

    public BootstrapService(AppUserService appUserService) {
        this.appUserService = appUserService;
    }

    @PostConstruct
    public void ensureInternalUser() {
        if (internalEmail == null || internalEmail.isBlank() ||
                internalPassword == null || internalPassword.isBlank()) {
            log.info("No bootstrap internal admin configured.");
            return;
        }
        appUserService.bootstrapInternalUser(internalEmail, internalPassword, internalName);
        log.info("Bootstrap internal admin ensured for " + internalEmail);
    }
}
