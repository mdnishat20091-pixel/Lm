CREATE TABLE IF NOT EXISTS users (
    id          BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    username    TEXT,
    first_name  TEXT,
    is_owner    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS providers (
    id               SERIAL PRIMARY KEY,
    slug             TEXT NOT NULL UNIQUE,
    name             TEXT NOT NULL,
    default_base_url TEXT,
    auth_header      TEXT NOT NULL,
    is_verified      BOOLEAN NOT NULL DEFAULT FALSE,
    position         INT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS provider_configs (
    id                 SERIAL PRIMARY KEY,
    provider_id        INT NOT NULL UNIQUE REFERENCES providers(id) ON DELETE CASCADE,
    base_url           TEXT,
    api_key_enc        TEXT,
    api_key_hint       TEXT,
    enabled            BOOLEAN NOT NULL DEFAULT FALSE,
    connection_status  TEXT NOT NULL DEFAULT 'unknown',
    last_connection_at TIMESTAMPTZ,
    last_error         TEXT,
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by         BIGINT
);

CREATE TABLE IF NOT EXISTS request_logs (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT,
    provider_id INT REFERENCES providers(id) ON DELETE SET NULL,
    action      TEXT NOT NULL,
    success     BOOLEAN NOT NULL,
    http_status INT,
    duration_ms INT,
    error_code  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_request_logs_created ON request_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_request_logs_provider ON request_logs (provider_id, created_at DESC);

CREATE TABLE IF NOT EXISTS settings (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT,
    action     TEXT NOT NULL,
    detail     TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs (created_at DESC);
