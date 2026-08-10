CREATE TABLE users (
    user_id        SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE claims (
    claim_id            SERIAL PRIMARY KEY,
    user_id             INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    claim_text          TEXT NOT NULL,
    submission_date     TIMESTAMP DEFAULT NOW(),
    verification_status VARCHAR(20) DEFAULT 'pending'
);

CREATE TABLE evidence (
    evidence_id       SERIAL PRIMARY KEY,
    claim_id          INTEGER REFERENCES claims(claim_id) ON DELETE CASCADE,
    source_name       VARCHAR(255),
    url               TEXT,
    extracted_text    TEXT,
    stance            VARCHAR(20),
    reliability_score DECIMAL(4,2)
);

CREATE TABLE reports (
    report_id        SERIAL PRIMARY KEY,
    claim_id         INTEGER REFERENCES claims(claim_id) ON DELETE CASCADE UNIQUE,
    final_result     VARCHAR(20),
    confidence_score DECIMAL(4,2),
    explanation      TEXT,
    created_at       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_claims_user ON claims(user_id);
CREATE INDEX idx_evidence_claim ON evidence(claim_id);
