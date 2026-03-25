-- وكيل المحتوى — Database Migration 001
-- المرجع: agents/content/docs/spec.md § ١٨-٢٠

-- ═══════════════════════════════════════════════════
-- 1. content_registry — ذاكرة الجمل الكنونية
-- ═══════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS content_registry (
    theme_slug        VARCHAR(100) NOT NULL,
    content_type      VARCHAR(100) NOT NULL,
    canonical_phrases JSONB        NOT NULL DEFAULT '{}',
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (theme_slug, content_type)
);

-- ═══════════════════════════════════════════════════
-- 2. content_pieces — المحتوى المُنتَج
-- ═══════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS content_pieces (
    content_id        UUID         PRIMARY KEY,
    request_id        UUID         NOT NULL,
    content_type      VARCHAR(100) NOT NULL,
    variant_label     VARCHAR(10),
    theme_slug        VARCHAR(100) NOT NULL,
    title             TEXT,
    body              TEXT         NOT NULL,
    metadata          JSONB        NOT NULL DEFAULT '{}',
    versioning        JSONB        NOT NULL DEFAULT '{}',
    structural_score  FLOAT        NOT NULL DEFAULT 0,
    language_score    FLOAT        NOT NULL DEFAULT 0,
    factual_score     FLOAT        NOT NULL DEFAULT 0,
    validation_score  FLOAT        NOT NULL DEFAULT 0,
    validation_issues JSONB        NOT NULL DEFAULT '[]',
    status            VARCHAR(50)  NOT NULL DEFAULT 'ready',
    target_agent      VARCHAR(100) NOT NULL,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════
-- 3. content_execution_log — Idempotency Guard
-- ═══════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS content_execution_log (
    idempotency_key VARCHAR(200) PRIMARY KEY,
    node_name       VARCHAR(100) NOT NULL,
    status          VARCHAR(50)  NOT NULL DEFAULT 'started',
    content_id      UUID,
    error_code      VARCHAR(100),
    error_detail    TEXT,
    started_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    failed_at       TIMESTAMPTZ
);

-- ═══════════════════════════════════════════════════
-- 4. content_review_queue — طابور المراجعة البشرية
-- ═══════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS content_review_queue (
    review_key       VARCHAR(200)  PRIMARY KEY,
    content_id       UUID          NOT NULL REFERENCES content_pieces(content_id),
    content_type     VARCHAR(100)  NOT NULL,
    theme_slug       VARCHAR(100),
    body_preview     TEXT,
    validation_score FLOAT         NOT NULL DEFAULT 0,
    requester        VARCHAR(255)  NOT NULL,
    correlation_id   VARCHAR(200)  NOT NULL,
    decision         VARCHAR(50),
    notes            TEXT,
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    decided_at       TIMESTAMPTZ
);

-- ═══════════════════════════════════════════════════
-- Indexes
-- ═══════════════════════════════════════════════════

CREATE INDEX IF NOT EXISTS idx_content_pieces_theme
    ON content_pieces (theme_slug, content_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_content_review_pending
    ON content_review_queue (created_at DESC) WHERE decision IS NULL;
