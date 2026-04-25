package com.bankparser.repository;

import com.bankparser.model.Statement;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface StatementRepository extends JpaRepository<Statement, Long> {
    List<Statement> findAllByOrderByCreatedAtDesc();
    List<Statement> findAllByOwnerIdOrderByCreatedAtDesc(Long ownerId);
    java.util.Optional<Statement> findByIdAndOwnerId(Long id, Long ownerId);
}
