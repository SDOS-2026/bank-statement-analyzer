-- Run this as postgres superuser:
-- sudo -u postgres psql -f setup_db.sql

-- Create user
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'bankparser') THEN
    CREATE USER bankparser WITH PASSWORD 'bankparser123';
  END IF;
END
$$;

-- Create database
CREATE DATABASE bankparser OWNER bankparser;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE bankparser TO bankparser;

\connect bankparser

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO bankparser;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bankparser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO bankparser;

-- Tables are auto-created by Spring Boot (ddl-auto=update)
-- But here they are for reference:

-- CREATE TABLE IF NOT EXISTS statements (
--   id                  BIGSERIAL PRIMARY KEY,
--   customer_name       VARCHAR(255),
--   bank_name           VARCHAR(255),
--   account_number      VARCHAR(100),
--   statement_period    VARCHAR(100),
--   analyst_name        VARCHAR(255),
--   notes               TEXT,
--   original_file_name  VARCHAR(500),
--   file_key            VARCHAR(500),
--   status              VARCHAR(50),
--   detected_bank       VARCHAR(100),
--   engine_used         VARCHAR(100),
--   confidence          DOUBLE PRECISION,
--   total_transactions  INTEGER,
--   balance_mismatches  INTEGER,
--   debit_total         DOUBLE PRECISION,
--   credit_total        DOUBLE PRECISION,
--   error_message       TEXT,
--   created_at          TIMESTAMP,
--   updated_at          TIMESTAMP
-- );

-- CREATE TABLE IF NOT EXISTS transactions (
--   id            BIGSERIAL PRIMARY KEY,
--   statement_id  BIGINT REFERENCES statements(id),
--   date          VARCHAR(50),
--   description   VARCHAR(1000),
--   debit         DOUBLE PRECISION,
--   credit        DOUBLE PRECISION,
--   balance       DOUBLE PRECISION,
--   reference     VARCHAR(500),
--   row_index     INTEGER
-- );

\echo 'Database setup complete!'
