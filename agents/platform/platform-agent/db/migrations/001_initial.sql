-- وكيل المنصة — Database Migration 001
-- المرجع: agents/platform/docs/spec.md § ٤، ٥
-- data-model.md v1.0.0

-- ════════════════════════════════════════════════════════════
-- 1. theme_registry — Single Source of Truth
-- ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS theme_registry (
    -- المفتاح الأساسي
    theme_slug              VARCHAR(100)    PRIMARY KEY,

    -- بيانات العرض
    theme_name_ar           TEXT            NOT NULL,
    domain                  VARCHAR(50)     NOT NULL,
    cluster                 VARCHAR(50)     NOT NULL,
    woocommerce_enabled     BOOLEAN         NOT NULL DEFAULT FALSE,
    cod_enabled             BOOLEAN         NOT NULL DEFAULT FALSE,

    -- WordPress (لا يظهر في أي حدث)
    wp_post_id              INTEGER         UNIQUE NOT NULL,
    wp_post_url             TEXT            NOT NULL,

    -- Lemon Squeezy
    ls_product_id           VARCHAR(50)     UNIQUE NOT NULL,
    ls_single_variant       VARCHAR(50)     NOT NULL,
    ls_unlimited_variant    VARCHAR(50)     NOT NULL,

    -- Versioning
    current_version         VARCHAR(20)     NOT NULL,
    contract_version        VARCHAR(20),

    -- Provenance (من أي حدث جاء هذا السجل)
    build_id                VARCHAR(100),
    approved_event_id       VARCHAR(100)    NOT NULL,
    launch_idempotency_key  VARCHAR(200),

    -- Update tracking
    last_updated_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    last_update_event_id    VARCHAR(100),
    last_update_idempotency_key VARCHAR(200),

    -- Timestamps
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- ════════════════════════════════════════════════════════════
-- 2. vip_registry — باقة VIP المجمّعة
-- ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS vip_registry (
    id              SERIAL          PRIMARY KEY,
    ls_product_id   VARCHAR(50)     UNIQUE NOT NULL,
    ls_variant_id   VARCHAR(50)     UNIQUE NOT NULL,
    theme_slugs     TEXT[]          NOT NULL DEFAULT '{}',
    last_updated_at TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- ════════════════════════════════════════════════════════════
-- 3. inconsistent_states — حالات التعارض
-- ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS inconsistent_states (
    id              SERIAL          PRIMARY KEY,
    theme_slug      VARCHAR(100)    NOT NULL,
    error_code      VARCHAR(20)     NOT NULL DEFAULT 'PLT_303',

    -- حالة كل نظام وقت الخطأ
    wp_state        JSONB,
    ls_state        JSONB,
    context         JSONB,

    -- إدارة الحل
    notified_at     TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ,                -- NULL = غير محلول
    resolution_note TEXT,

    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- ════════════════════════════════════════════════════════════
-- 4. execution_log — Idempotency Guard
-- ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS execution_log (
    idempotency_key     VARCHAR(200)    PRIMARY KEY,
    node_name           VARCHAR(100)    NOT NULL,
    status              VARCHAR(20)     NOT NULL,   -- started | completed | failed
    last_completed_node VARCHAR(100),
    result_snapshot     JSONB,
    error_code          VARCHAR(20),
    started_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ
);

-- ════════════════════════════════════════════════════════════
-- 5. notification_log — منع تكرار الإيميلات
-- ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS notification_log (
    id              SERIAL          PRIMARY KEY,
    buyer_email     TEXT            NOT NULL,
    theme_slug      VARCHAR(100)    NOT NULL,
    version         VARCHAR(20)     NOT NULL,
    sent_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    UNIQUE(buyer_email, theme_slug, version)
);

-- ════════════════════════════════════════════════════════════
-- Indexes
-- ════════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS idx_theme_registry_ls_product
    ON theme_registry(ls_product_id);

CREATE INDEX IF NOT EXISTS idx_inconsistent_states_unresolved
    ON inconsistent_states(theme_slug, resolved_at)
    WHERE resolved_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_execution_log_key_node
    ON execution_log(idempotency_key, node_name);

CREATE INDEX IF NOT EXISTS idx_notification_log_email_theme
    ON notification_log(buyer_email, theme_slug);
