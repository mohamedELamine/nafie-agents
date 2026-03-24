-- === db/001_initial.sql ===
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

-- === db/001_supervisor_tables.sql ===
-- Create supervisor tables

CREATE TABLE IF NOT EXISTS workflow_instances (
    instance_id VARCHAR(100) PRIMARY KEY,
    workflow_type VARCHAR(50) NOT NULL,
    business_key VARCHAR(200) UNIQUE NOT NULL,
    theme_slug VARCHAR(100),
    correlation_id VARCHAR(100),
    current_step INTEGER DEFAULT 0,
    total_steps INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    failed_step INTEGER,
    failure_reason TEXT,
    retry_count INTEGER DEFAULT 0,
    context JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_workflow_business_key ON workflow_instances(business_key);
CREATE INDEX idx_workflow_status ON workflow_instances(status);
CREATE INDEX idx_workflow_type ON workflow_instances(workflow_type);

CREATE TABLE IF NOT EXISTS workflow_step_history (
    step_id SERIAL PRIMARY KEY,
    instance_id VARCHAR(100) NOT NULL,
    step_number INTEGER NOT NULL,
    agent_name VARCHAR(100) NOT NULL,
    action VARCHAR(200) NOT NULL,
    status VARCHAR(50) NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error TEXT
);

CREATE INDEX idx_step_instance ON workflow_step_history(instance_id);

CREATE TABLE IF NOT EXISTS supervisor_audit_log (
    log_id VARCHAR(100) PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    action VARCHAR(200) NOT NULL,
    target VARCHAR(200) NOT NULL,
    workflow_id VARCHAR(100),
    correlation_id VARCHAR(100),
    details JSONB,
    outcome VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_category ON supervisor_audit_log(category);
CREATE INDEX idx_audit_workflow ON supervisor_audit_log(workflow_id);
CREATE INDEX idx_audit_created ON supervisor_audit_log(created_at DESC);

CREATE TABLE IF NOT EXISTS conflict_records (
    conflict_id VARCHAR(100) PRIMARY KEY,
    conflict_type VARCHAR(50) NOT NULL,
    agents_involved TEXT NOT NULL,
    description TEXT NOT NULL,
    resolution TEXT,
    resolved_at TIMESTAMP,
    escalated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_conflict_type ON conflict_records(conflict_type);
CREATE INDEX idx_conflict_resolved ON conflict_records(resolved_at);

CREATE TABLE IF NOT EXISTS agent_health (
    agent_name VARCHAR(100) PRIMARY KEY,
    status VARCHAR(50) NOT NULL,
    last_heartbeat TIMESTAMP,
    queue_depth INTEGER DEFAULT 0,
    active_jobs INTEGER DEFAULT 0,
    error_rate FLOAT DEFAULT 0.0,
    mode VARCHAR(50) DEFAULT 'normal',
    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    issues TEXT
);

CREATE INDEX idx_health_status ON agent_health(status);

CREATE TABLE IF NOT EXISTS policy_rules (
    policy_id VARCHAR(100) PRIMARY KEY,
    rule_type VARCHAR(50) NOT NULL,
    condition JSONB NOT NULL,
    action VARCHAR(200) NOT NULL,
    value FLOAT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE INDEX idx_policy_active ON policy_rules(active);

-- === db/001_analytics_tables.sql ===
-- Analytics Tables Migration
-- Created: 2026-03-22

-- ── analytics_events ─────────────────────────────────────────────────────────
-- theme_slug nullable: بعض الأحداث بلا قالب محدد (مثل CAMPAIGN_LAUNCHED العامة)
CREATE TABLE IF NOT EXISTS analytics_events (
    event_id     VARCHAR(255) PRIMARY KEY,
    event_type   VARCHAR(100) NOT NULL,
    source_agent VARCHAR(100) NOT NULL,
    theme_slug   VARCHAR(255),                         -- nullable
    raw_data     JSONB        NOT NULL DEFAULT '{}',
    occurred_at  TIMESTAMPTZ  NOT NULL,                -- وقت الحدث الحقيقي — للتحليل
    received_at  TIMESTAMPTZ  NOT NULL,                -- وقت الاستلام — للتشخيص
    processed    BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ae_occurred_at  ON analytics_events (occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_ae_event_type   ON analytics_events (event_type);
CREATE INDEX IF NOT EXISTS idx_ae_theme_slug   ON analytics_events (theme_slug) WHERE theme_slug IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ae_received_at  ON analytics_events (received_at DESC);

-- ── metric_snapshots ──────────────────────────────────────────────────────────
-- Unique constraint لـ idempotency: نفس المقياس + granularity + period + dimensions
CREATE TABLE IF NOT EXISTS metric_snapshots (
    metric_id    VARCHAR(255) PRIMARY KEY,
    metric_key   VARCHAR(100) NOT NULL,
    theme_slug   VARCHAR(255),                         -- nullable
    channel      VARCHAR(100),                         -- nullable
    granularity  VARCHAR(20)  NOT NULL,                -- "hour" | "day" | "week" | "month"
    period_start TIMESTAMPTZ  NOT NULL,
    period_end   TIMESTAMPTZ  NOT NULL,
    value        NUMERIC(20,6) NOT NULL,
    unit         VARCHAR(50)  NOT NULL,
    computed_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (metric_key, granularity, period_start, theme_slug, channel)
);

CREATE INDEX IF NOT EXISTS idx_ms_metric_key   ON metric_snapshots (metric_key);
CREATE INDEX IF NOT EXISTS idx_ms_period       ON metric_snapshots (period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_ms_theme_slug   ON metric_snapshots (theme_slug) WHERE theme_slug IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ms_granularity  ON metric_snapshots (granularity);

-- ── analytics_patterns ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS analytics_patterns (
    pattern_id         VARCHAR(255) PRIMARY KEY,
    pattern_type       VARCHAR(100) NOT NULL,
    analytics_type     VARCHAR(50)  NOT NULL,          -- "operational" | "business"
    theme_slug         VARCHAR(255),                   -- nullable
    channel            VARCHAR(100),                   -- nullable
    description        TEXT         NOT NULL DEFAULT '',
    confidence         NUMERIC(4,3) NOT NULL,          -- 0.000 - 1.000
    supporting_metrics JSONB        NOT NULL DEFAULT '[]',
    detected_at        TIMESTAMPTZ  NOT NULL,
    is_actionable      BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ap_detected_at    ON analytics_patterns (detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_ap_type           ON analytics_patterns (pattern_type);
CREATE INDEX IF NOT EXISTS idx_ap_analytics_type ON analytics_patterns (analytics_type);

-- ── analytics_signals ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS analytics_signals (
    signal_id             VARCHAR(255) PRIMARY KEY,
    signal_type           VARCHAR(100) NOT NULL,
    priority              VARCHAR(20)  NOT NULL,       -- "immediate" | "daily" | "weekly"
    target_agent          VARCHAR(100) NOT NULL,
    theme_slug            VARCHAR(255),               -- nullable
    channel               VARCHAR(100),               -- nullable
    recommendation        TEXT         NOT NULL DEFAULT '',
    confidence            NUMERIC(4,3) NOT NULL DEFAULT 0.5,
    supporting_pattern_id VARCHAR(255),               -- nullable FK إلى analytics_patterns
    data                  JSONB        NOT NULL DEFAULT '{}',
    generated_at          TIMESTAMPTZ  NOT NULL,
    sent_at               TIMESTAMPTZ,               -- NULL = لم يُرسَل بعد
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_as_generated_at  ON analytics_signals (generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_as_signal_type   ON analytics_signals (signal_type);
CREATE INDEX IF NOT EXISTS idx_as_target_agent  ON analytics_signals (target_agent);
CREATE INDEX IF NOT EXISTS idx_as_sent_at       ON analytics_signals (sent_at) WHERE sent_at IS NOT NULL;

-- ── attribution_records ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS attribution_records (
    sale_id                VARCHAR(255) PRIMARY KEY,
    theme_slug             VARCHAR(255) NOT NULL,
    amount_usd             NUMERIC(12,2) NOT NULL DEFAULT 0,
    license_tier           VARCHAR(100) NOT NULL DEFAULT 'unknown',
    channels_touched       JSONB        NOT NULL DEFAULT '[]',
    attributed_to          VARCHAR(100) NOT NULL,
    attribution_model      VARCHAR(50)  NOT NULL DEFAULT 'last_touch_v1',
    attribution_confidence VARCHAR(20)  NOT NULL,      -- "high" | "medium" | "low"
    attribution_note       TEXT         NOT NULL DEFAULT '',
    sale_date              TIMESTAMPTZ  NOT NULL,      -- من occurred_at
    created_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ar_theme_slug  ON attribution_records (theme_slug);
CREATE INDEX IF NOT EXISTS idx_ar_sale_date   ON attribution_records (sale_date DESC);
CREATE INDEX IF NOT EXISTS idx_ar_attributed  ON attribution_records (attributed_to);

-- ── signal_outcomes ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS signal_outcomes (
    outcome_id          VARCHAR(255) PRIMARY KEY,
    signal_id           VARCHAR(255) NOT NULL REFERENCES analytics_signals (signal_id),
    target_agent        VARCHAR(100) NOT NULL DEFAULT '',
    action_taken        TEXT,                          -- nullable
    observed_metric     VARCHAR(100),                  -- nullable
    before_value        NUMERIC(20,6),                 -- nullable
    after_value         NUMERIC(20,6),                 -- nullable
    outcome_window_days INTEGER      NOT NULL DEFAULT 7,
    success_score       NUMERIC(4,3),                  -- nullable: 0.000 - 1.000
    evaluated_at        TIMESTAMPTZ,                   -- nullable: لم يُقيَّم بعد
    notes               TEXT,                          -- nullable
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_so_signal_id    ON signal_outcomes (signal_id);
CREATE INDEX IF NOT EXISTS idx_so_evaluated_at ON signal_outcomes (evaluated_at DESC);

-- ── weekly_reports ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS weekly_reports (
    report_id       VARCHAR(255) PRIMARY KEY,
    period_start    TIMESTAMPTZ  NOT NULL,
    period_end      TIMESTAMPTZ  NOT NULL,
    total_sales     INTEGER      NOT NULL DEFAULT 0,
    total_revenue   NUMERIC(14,2) NOT NULL DEFAULT 0,
    top_theme       VARCHAR(255),                      -- nullable
    top_channel     VARCHAR(100),                      -- nullable
    support_tickets INTEGER      NOT NULL DEFAULT 0,
    escalation_rate NUMERIC(5,4) NOT NULL DEFAULT 0,   -- ratio: 0.0000 - 1.0000
    new_products    INTEGER      NOT NULL DEFAULT 0,
    signals_sent    INTEGER      NOT NULL DEFAULT 0,
    highlights      JSONB        NOT NULL DEFAULT '[]',
    concerns        JSONB        NOT NULL DEFAULT '[]',
    generated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wr_period       ON weekly_reports (period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_wr_generated_at ON weekly_reports (generated_at DESC);

-- === db/001_support_tables.sql ===
-- Support Tables Migration
-- Created: 2026-03-22

-- Table: support_execution_log
CREATE TABLE IF NOT EXISTS support_execution_log (
    execution_id VARCHAR(255) PRIMARY KEY,
    ticket_id VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for execution queries
CREATE INDEX IF NOT EXISTS idx_execution_log_ticket ON support_execution_log(ticket_id);
CREATE INDEX IF NOT EXISTS idx_execution_log_platform ON support_execution_log(platform);
CREATE INDEX IF NOT EXISTS idx_execution_log_status ON support_execution_log(status);
CREATE INDEX IF NOT EXISTS idx_execution_log_started ON support_execution_log(started_at DESC);

-- Table: support_escalation_log
CREATE TABLE IF NOT EXISTS support_escalation_log (
    escalation_id VARCHAR(255) PRIMARY KEY,
    ticket_id VARCHAR(255) NOT NULL,
    ticket_platform VARCHAR(50) NOT NULL,
    escalation_reason VARCHAR(100) NOT NULL,
    original_message TEXT,
    customer_identity JSONB,
    current_agent_context TEXT,
    escalation_time TIMESTAMP WITH TIME ZONE NOT NULL,
    resolution_status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for escalation queries
CREATE INDEX IF NOT EXISTS idx_escalation_log_ticket ON support_escalation_log(ticket_id);
CREATE INDEX IF NOT EXISTS idx_escalation_log_reason ON support_escalation_log(escalation_reason);
CREATE INDEX IF NOT EXISTS idx_escalation_log_time ON support_escalation_log(escalation_time DESC);

-- Table: support_knowledge_log
CREATE TABLE IF NOT EXISTS support_knowledge_log (
    update_id VARCHAR(255) PRIMARY KEY,
    collection VARCHAR(50) NOT NULL,
    document_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for knowledge queries
CREATE INDEX IF NOT EXISTS idx_knowledge_log_collection ON support_knowledge_log(collection);
CREATE INDEX IF NOT EXISTS idx_knowledge_log_created ON support_knowledge_log(created_at DESC);
-- === db/001_marketing_tables.sql ===
-- Marketing Tables Migration
-- Created: 2026-03-22

-- Table: marketing_calendar
CREATE TABLE IF NOT EXISTS marketing_calendar (
    campaign_id VARCHAR(255) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    theme_slug VARCHAR(255) NOT NULL,
    content_snapshot JSONB,
    assets_snapshot JSONB,
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) DEFAULT 'draft',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for campaign queries
CREATE INDEX IF NOT EXISTS idx_marketing_calendar_status ON marketing_calendar(status);
CREATE INDEX IF NOT EXISTS idx_marketing_calendar_theme_slug ON marketing_calendar(theme_slug);
CREATE INDEX IF NOT EXISTS idx_marketing_calendar_start_date ON marketing_calendar(start_date);

-- Table: scheduled_posts
CREATE TABLE IF NOT EXISTS scheduled_posts (
    post_id VARCHAR(255) PRIMARY KEY,
    campaign_id VARCHAR(255) NOT NULL,
    channel VARCHAR(100) NOT NULL,
    format VARCHAR(50) NOT NULL,
    scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
    content_snapshot_id VARCHAR(255),
    asset_snapshot_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',
    variant_label VARCHAR(100),
    scheduled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    published_at TIMESTAMP WITH TIME ZONE,
    failure_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for post queries
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_campaign_id ON scheduled_posts(campaign_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_status ON scheduled_posts(status);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_scheduled_time ON scheduled_posts(scheduled_time);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_channel ON scheduled_posts(channel);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_content_snapshot_id ON scheduled_posts(content_snapshot_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_asset_snapshot_id ON scheduled_posts(asset_snapshot_id);

-- Table: campaign_log
CREATE TABLE IF NOT EXISTS campaign_log (
    log_id VARCHAR(255) PRIMARY KEY,
    campaign_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for log queries
CREATE INDEX IF NOT EXISTS idx_campaign_log_campaign_id ON campaign_log(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_log_event_type ON campaign_log(event_type);
CREATE INDEX IF NOT EXISTS idx_campaign_log_created_at ON campaign_log(created_at);
-- === db/001_content_tables.sql ===
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

-- === db/001_visual_tables.sql ===
-- Create visual production tables

CREATE TABLE IF NOT EXISTS asset_manifest (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(100) UNIQUE NOT NULL,
    theme_slug VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    total_cost FLOAT DEFAULT 0.0,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    assets_json JSONB
);

CREATE INDEX IF NOT EXISTS idx_asset_manifest_batch ON asset_manifest(batch_id);
CREATE INDEX IF NOT EXISTS idx_asset_manifest_theme ON asset_manifest(theme_slug);
CREATE INDEX IF NOT EXISTS idx_asset_manifest_status ON asset_manifest(status);

CREATE TABLE IF NOT EXISTS asset_assets (
    id SERIAL PRIMARY KEY,
    asset_id VARCHAR(100) NOT NULL,
    manifest_id INTEGER REFERENCES asset_manifest(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    url VARCHAR(500) NOT NULL,
    dimensions JSONB,
    size_kb FLOAT NOT NULL,
    quality_score FLOAT NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_asset_assets_manifest ON asset_assets(manifest_id);
CREATE INDEX IF NOT EXISTS idx_asset_assets_type ON asset_assets(type);
CREATE INDEX IF NOT EXISTS idx_asset_assets_status ON asset_assets(status);

CREATE TABLE IF NOT EXISTS visual_review_queue (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(100) UNIQUE NOT NULL,
    theme_slug VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    manifest_json JSONB NOT NULL,
    review_decision VARCHAR(50),
    review_notes TEXT,
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_visual_review_batch ON visual_review_queue(batch_id);
CREATE INDEX IF NOT EXISTS idx_visual_review_decision ON visual_review_queue(review_decision);

