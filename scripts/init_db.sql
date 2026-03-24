-- منظومة القوالب العربية — التهيئة الأولية لقاعدة البيانات
-- تم توليد هذا الملف من الجداول المرجعية داخل db/ لكل وكيل.

BEGIN;

-- ============================================================================
-- Platform Agent
-- ============================================================================

CREATE TABLE IF NOT EXISTS theme_registry (
    theme_slug                  VARCHAR(100) PRIMARY KEY,
    theme_name_ar               TEXT NOT NULL,
    domain                      VARCHAR(50) NOT NULL,
    cluster                     VARCHAR(50) NOT NULL,
    woocommerce_enabled         BOOLEAN NOT NULL DEFAULT FALSE,
    cod_enabled                 BOOLEAN NOT NULL DEFAULT FALSE,
    wp_post_id                  INTEGER UNIQUE NOT NULL,
    wp_post_url                 TEXT NOT NULL,
    ls_product_id               VARCHAR(50) UNIQUE NOT NULL,
    ls_single_variant           VARCHAR(50) NOT NULL,
    ls_unlimited_variant        VARCHAR(50) NOT NULL,
    current_version             VARCHAR(20) NOT NULL,
    contract_version            VARCHAR(20),
    build_id                    VARCHAR(100),
    approved_event_id           VARCHAR(100) NOT NULL,
    launch_idempotency_key      VARCHAR(200),
    last_updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_update_event_id        VARCHAR(100),
    last_update_idempotency_key VARCHAR(200),
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vip_registry (
    id              SERIAL PRIMARY KEY,
    ls_product_id   VARCHAR(50) UNIQUE NOT NULL,
    ls_variant_id   VARCHAR(50) UNIQUE NOT NULL,
    theme_slugs     TEXT[] NOT NULL DEFAULT '{}',
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS inconsistent_states (
    id              SERIAL PRIMARY KEY,
    theme_slug      VARCHAR(100) NOT NULL,
    error_code      VARCHAR(20) NOT NULL DEFAULT 'PLT_303',
    wp_state        JSONB,
    ls_state        JSONB,
    context         JSONB,
    notified_at     TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ,
    resolution_note TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS execution_log (
    idempotency_key     VARCHAR(200) PRIMARY KEY,
    node_name           VARCHAR(100) NOT NULL,
    status              VARCHAR(20) NOT NULL,
    last_completed_node VARCHAR(100),
    result_snapshot     JSONB,
    error_code          VARCHAR(20),
    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS notification_log (
    id          SERIAL PRIMARY KEY,
    buyer_email TEXT NOT NULL,
    theme_slug  VARCHAR(100) NOT NULL,
    version     VARCHAR(20) NOT NULL,
    sent_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (buyer_email, theme_slug, version)
);

CREATE INDEX IF NOT EXISTS idx_theme_registry_ls_product_id
    ON theme_registry(ls_product_id);
CREATE INDEX IF NOT EXISTS idx_inconsistent_states_theme_slug
    ON inconsistent_states(theme_slug);
CREATE INDEX IF NOT EXISTS idx_inconsistent_states_unresolved
    ON inconsistent_states(theme_slug, resolved_at)
    WHERE resolved_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_notification_log_theme_slug
    ON notification_log(theme_slug);

-- ============================================================================
-- Content Agent
-- ============================================================================

CREATE TABLE IF NOT EXISTS content_registry (
    theme_slug        VARCHAR(100) NOT NULL,
    content_type      VARCHAR(100) NOT NULL,
    canonical_phrases JSONB NOT NULL DEFAULT '{}',
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (theme_slug, content_type)
);

CREATE TABLE IF NOT EXISTS content_pieces (
    content_id        UUID PRIMARY KEY,
    request_id        UUID NOT NULL,
    content_type      VARCHAR(100) NOT NULL,
    variant_label     VARCHAR(10),
    theme_slug        VARCHAR(100) NOT NULL,
    title             TEXT,
    body              TEXT NOT NULL,
    metadata          JSONB NOT NULL DEFAULT '{}',
    versioning        JSONB NOT NULL DEFAULT '{}',
    structural_score  FLOAT NOT NULL DEFAULT 0,
    language_score    FLOAT NOT NULL DEFAULT 0,
    factual_score     FLOAT NOT NULL DEFAULT 0,
    validation_score  FLOAT NOT NULL DEFAULT 0,
    validation_issues JSONB NOT NULL DEFAULT '[]',
    status            VARCHAR(50) NOT NULL DEFAULT 'ready',
    target_agent      VARCHAR(100) NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS content_execution_log (
    idempotency_key VARCHAR(200) PRIMARY KEY,
    node_name       VARCHAR(100) NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'started',
    content_id      UUID,
    error_code      VARCHAR(100),
    error_detail    TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    failed_at       TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS content_review_queue (
    review_key       VARCHAR(200) PRIMARY KEY,
    content_id       UUID NOT NULL REFERENCES content_pieces(content_id),
    content_type     VARCHAR(100) NOT NULL,
    theme_slug       VARCHAR(100),
    body_preview     TEXT,
    validation_score FLOAT NOT NULL DEFAULT 0,
    requester        VARCHAR(255) NOT NULL,
    correlation_id   VARCHAR(200) NOT NULL,
    decision         VARCHAR(50),
    notes            TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at       TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_content_pieces_theme_slug
    ON content_pieces(theme_slug);
CREATE INDEX IF NOT EXISTS idx_content_registry_theme_slug
    ON content_registry(theme_slug);
CREATE INDEX IF NOT EXISTS idx_content_review_queue_theme_slug
    ON content_review_queue(theme_slug);
CREATE INDEX IF NOT EXISTS idx_content_review_queue_pending
    ON content_review_queue(created_at DESC)
    WHERE decision IS NULL;

-- ============================================================================
-- Marketing Agent
-- ============================================================================

CREATE TABLE IF NOT EXISTS marketing_calendar (
    campaign_id       VARCHAR(255) PRIMARY KEY,
    title             VARCHAR(255) NOT NULL,
    theme_slug        VARCHAR(255) NOT NULL,
    content_snapshot  JSONB,
    assets_snapshot   JSONB,
    start_date        TIMESTAMPTZ NOT NULL,
    end_date          TIMESTAMPTZ NOT NULL,
    status            VARCHAR(50) DEFAULT 'draft',
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scheduled_posts (
    post_id              VARCHAR(255) PRIMARY KEY,
    campaign_id          VARCHAR(255) NOT NULL,
    channel              VARCHAR(100) NOT NULL,
    format               VARCHAR(50) NOT NULL,
    scheduled_time       TIMESTAMPTZ NOT NULL,
    content_snapshot_id  VARCHAR(255),
    asset_snapshot_id    VARCHAR(255),
    status               VARCHAR(50) DEFAULT 'pending',
    variant_label        VARCHAR(100),
    scheduled_at         TIMESTAMPTZ DEFAULT NOW(),
    published_at         TIMESTAMPTZ,
    failure_reason       TEXT,
    created_at           TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS campaign_log (
    log_id       VARCHAR(255) PRIMARY KEY,
    campaign_id  VARCHAR(255) NOT NULL,
    event_type   VARCHAR(100) NOT NULL,
    details      JSONB,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_marketing_calendar_theme_slug
    ON marketing_calendar(theme_slug);
CREATE INDEX IF NOT EXISTS idx_marketing_calendar_status
    ON marketing_calendar(status);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_scheduled_time
    ON scheduled_posts(scheduled_time);
CREATE INDEX IF NOT EXISTS idx_campaign_log_created_at
    ON campaign_log(created_at);

-- ============================================================================
-- Analytics Agent
-- ============================================================================

CREATE TABLE IF NOT EXISTS analytics_events (
    event_id     VARCHAR(255) PRIMARY KEY,
    event_type   VARCHAR(100) NOT NULL,
    source_agent VARCHAR(100) NOT NULL,
    theme_slug   VARCHAR(255),
    raw_data     JSONB NOT NULL DEFAULT '{}',
    occurred_at  TIMESTAMPTZ NOT NULL,
    received_at  TIMESTAMPTZ NOT NULL,
    processed    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS metric_snapshots (
    metric_id    VARCHAR(255) PRIMARY KEY,
    metric_key   VARCHAR(100) NOT NULL,
    theme_slug   VARCHAR(255),
    channel      VARCHAR(100),
    granularity  VARCHAR(20) NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end   TIMESTAMPTZ NOT NULL,
    value        NUMERIC(20, 6) NOT NULL,
    unit         VARCHAR(50) NOT NULL,
    computed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (metric_key, granularity, period_start, theme_slug, channel)
);

CREATE TABLE IF NOT EXISTS analytics_patterns (
    pattern_id         VARCHAR(255) PRIMARY KEY,
    pattern_type       VARCHAR(100) NOT NULL,
    analytics_type     VARCHAR(50) NOT NULL,
    theme_slug         VARCHAR(255),
    channel            VARCHAR(100),
    description        TEXT NOT NULL DEFAULT '',
    confidence         NUMERIC(4, 3) NOT NULL,
    supporting_metrics JSONB NOT NULL DEFAULT '[]',
    detected_at        TIMESTAMPTZ NOT NULL,
    is_actionable      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analytics_signals (
    signal_id             VARCHAR(255) PRIMARY KEY,
    signal_type           VARCHAR(100) NOT NULL,
    priority              VARCHAR(20) NOT NULL,
    target_agent          VARCHAR(100) NOT NULL,
    theme_slug            VARCHAR(255),
    channel               VARCHAR(100),
    recommendation        TEXT NOT NULL DEFAULT '',
    confidence            NUMERIC(4, 3) NOT NULL DEFAULT 0.5,
    supporting_pattern_id VARCHAR(255),
    data                  JSONB NOT NULL DEFAULT '{}',
    generated_at          TIMESTAMPTZ NOT NULL,
    sent_at               TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS attribution_records (
    sale_id                VARCHAR(255) PRIMARY KEY,
    theme_slug             VARCHAR(255) NOT NULL,
    amount_usd             NUMERIC(12, 2) NOT NULL DEFAULT 0,
    license_tier           VARCHAR(100) NOT NULL DEFAULT 'unknown',
    channels_touched       JSONB NOT NULL DEFAULT '[]',
    attributed_to          VARCHAR(100) NOT NULL,
    attribution_model      VARCHAR(50) NOT NULL DEFAULT 'last_touch_v1',
    attribution_confidence VARCHAR(20) NOT NULL,
    attribution_note       TEXT NOT NULL DEFAULT '',
    sale_date              TIMESTAMPTZ NOT NULL,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS signal_outcomes (
    outcome_id          VARCHAR(255) PRIMARY KEY,
    signal_id           VARCHAR(255) NOT NULL REFERENCES analytics_signals(signal_id),
    target_agent        VARCHAR(100) NOT NULL DEFAULT '',
    action_taken        TEXT,
    observed_metric     VARCHAR(100),
    before_value        NUMERIC(20, 6),
    after_value         NUMERIC(20, 6),
    outcome_window_days INTEGER NOT NULL DEFAULT 7,
    success_score       NUMERIC(4, 3),
    evaluated_at        TIMESTAMPTZ,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS weekly_reports (
    report_id        VARCHAR(255) PRIMARY KEY,
    period_start     TIMESTAMPTZ NOT NULL,
    period_end       TIMESTAMPTZ NOT NULL,
    total_sales      INTEGER NOT NULL DEFAULT 0,
    total_revenue    NUMERIC(14, 2) NOT NULL DEFAULT 0,
    top_theme        VARCHAR(255),
    top_channel      VARCHAR(100),
    support_tickets  INTEGER NOT NULL DEFAULT 0,
    escalation_rate  NUMERIC(5, 4) NOT NULL DEFAULT 0,
    new_products     INTEGER NOT NULL DEFAULT 0,
    signals_sent     INTEGER NOT NULL DEFAULT 0,
    highlights       JSONB NOT NULL DEFAULT '[]',
    concerns         JSONB NOT NULL DEFAULT '[]',
    generated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analytics_events_theme_slug
    ON analytics_events(theme_slug);
CREATE INDEX IF NOT EXISTS idx_analytics_events_occurred_at
    ON analytics_events(occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_metric_snapshots_theme_slug
    ON metric_snapshots(theme_slug);
CREATE INDEX IF NOT EXISTS idx_analytics_patterns_theme_slug
    ON analytics_patterns(theme_slug);
CREATE INDEX IF NOT EXISTS idx_analytics_signals_theme_slug
    ON analytics_signals(theme_slug);
CREATE INDEX IF NOT EXISTS idx_analytics_signals_generated_at
    ON analytics_signals(generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_attribution_records_theme_slug
    ON attribution_records(theme_slug);
CREATE INDEX IF NOT EXISTS idx_signal_outcomes_signal_id
    ON signal_outcomes(signal_id);
CREATE INDEX IF NOT EXISTS idx_weekly_reports_generated_at
    ON weekly_reports(generated_at DESC);

-- ============================================================================
-- Support Agent
-- ============================================================================

CREATE TABLE IF NOT EXISTS support_execution_log (
    execution_id   VARCHAR(255) PRIMARY KEY,
    ticket_id      VARCHAR(255) NOT NULL,
    platform       VARCHAR(50) NOT NULL,
    started_at     TIMESTAMPTZ NOT NULL,
    completed_at   TIMESTAMPTZ,
    status         VARCHAR(50) DEFAULT 'pending',
    error_message  TEXT,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS support_escalation_log (
    escalation_id         VARCHAR(255) PRIMARY KEY,
    ticket_id             VARCHAR(255) NOT NULL,
    ticket_platform       VARCHAR(50) NOT NULL,
    escalation_reason     VARCHAR(100) NOT NULL,
    original_message      TEXT,
    customer_identity     JSONB,
    current_agent_context TEXT,
    escalation_time       TIMESTAMPTZ NOT NULL,
    resolution_status     VARCHAR(50) DEFAULT 'pending',
    created_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS support_knowledge_log (
    update_id    VARCHAR(255) PRIMARY KEY,
    collection   VARCHAR(50) NOT NULL,
    document_id  VARCHAR(255) NOT NULL,
    content      TEXT NOT NULL,
    metadata     JSONB,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_support_execution_log_ticket_id
    ON support_execution_log(ticket_id);
CREATE INDEX IF NOT EXISTS idx_support_escalation_log_ticket_id
    ON support_escalation_log(ticket_id);
CREATE INDEX IF NOT EXISTS idx_support_escalation_log_time
    ON support_escalation_log(escalation_time DESC);

-- ============================================================================
-- Visual Production Agent
-- ============================================================================

CREATE TABLE IF NOT EXISTS asset_manifest (
    id          SERIAL PRIMARY KEY,
    batch_id    VARCHAR(100) UNIQUE NOT NULL,
    theme_slug  VARCHAR(100) NOT NULL,
    version     VARCHAR(50) NOT NULL,
    total_cost  FLOAT DEFAULT 0.0,
    status      VARCHAR(50) DEFAULT 'pending',
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    notes       TEXT,
    assets_json JSONB
);

CREATE TABLE IF NOT EXISTS asset_assets (
    id           SERIAL PRIMARY KEY,
    asset_id     VARCHAR(100) NOT NULL,
    manifest_id  INTEGER REFERENCES asset_manifest(id) ON DELETE CASCADE,
    type         VARCHAR(50) NOT NULL,
    url          VARCHAR(500) NOT NULL,
    dimensions   JSONB,
    size_kb      FLOAT NOT NULL,
    quality_score FLOAT NOT NULL,
    status       VARCHAR(50) NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS visual_review_queue (
    id              SERIAL PRIMARY KEY,
    batch_id        VARCHAR(100) UNIQUE NOT NULL,
    theme_slug      VARCHAR(100) NOT NULL,
    version         VARCHAR(50) NOT NULL,
    manifest_json   JSONB NOT NULL,
    review_decision VARCHAR(50),
    review_notes    TEXT,
    reviewed_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS batch_log (
    batch_id          VARCHAR(100) PRIMARY KEY,
    theme_slug        VARCHAR(100) NOT NULL,
    started_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at      TIMESTAMPTZ,
    budget_used       NUMERIC(12, 4) NOT NULL DEFAULT 0,
    assets_count      INTEGER NOT NULL DEFAULT 0,
    generated_assets  INTEGER NOT NULL DEFAULT 0,
    quality_approved  INTEGER NOT NULL DEFAULT 0,
    quality_rejected  INTEGER NOT NULL DEFAULT 0,
    status            VARCHAR(50) NOT NULL DEFAULT 'pending',
    error_message     TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_asset_manifest_theme_slug
    ON asset_manifest(theme_slug);
CREATE INDEX IF NOT EXISTS idx_visual_review_queue_theme_slug
    ON visual_review_queue(theme_slug);
CREATE INDEX IF NOT EXISTS idx_batch_log_theme_slug
    ON batch_log(theme_slug);

-- ============================================================================
-- Supervisor Agent
-- ============================================================================

CREATE TABLE IF NOT EXISTS workflow_instances (
    instance_id     VARCHAR(100) PRIMARY KEY,
    workflow_type   VARCHAR(50) NOT NULL,
    business_key    VARCHAR(200) UNIQUE NOT NULL,
    theme_slug      VARCHAR(100),
    correlation_id  VARCHAR(100),
    current_step    INTEGER DEFAULT 0,
    total_steps     INTEGER DEFAULT 0,
    status          VARCHAR(50) DEFAULT 'pending',
    started_at      TIMESTAMP,
    completed_at    TIMESTAMP,
    failed_step     INTEGER,
    failure_reason  TEXT,
    retry_count     INTEGER DEFAULT 0,
    context         JSONB,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workflow_step_history (
    step_id        SERIAL PRIMARY KEY,
    instance_id    VARCHAR(100) NOT NULL,
    step_number    INTEGER NOT NULL,
    agent_name     VARCHAR(100) NOT NULL,
    action         VARCHAR(200) NOT NULL,
    status         VARCHAR(50) NOT NULL,
    started_at     TIMESTAMP,
    completed_at   TIMESTAMP,
    error          TEXT
);

CREATE TABLE IF NOT EXISTS supervisor_audit_log (
    log_id          VARCHAR(100) PRIMARY KEY,
    category        VARCHAR(50) NOT NULL,
    action          VARCHAR(200) NOT NULL,
    target          VARCHAR(200) NOT NULL,
    workflow_id     VARCHAR(100),
    correlation_id  VARCHAR(100),
    details         JSONB,
    outcome         VARCHAR(50),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conflict_records (
    conflict_id      VARCHAR(100) PRIMARY KEY,
    conflict_type    VARCHAR(50) NOT NULL,
    agents_involved  TEXT NOT NULL,
    description      TEXT NOT NULL,
    resolution       TEXT,
    resolved_at      TIMESTAMP,
    escalated        BOOLEAN DEFAULT FALSE,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_health (
    agent_name      VARCHAR(100) PRIMARY KEY,
    status          VARCHAR(50) NOT NULL,
    last_heartbeat  TIMESTAMP,
    queue_depth     INTEGER DEFAULT 0,
    active_jobs     INTEGER DEFAULT 0,
    error_rate      FLOAT DEFAULT 0.0,
    mode            VARCHAR(50) DEFAULT 'normal',
    last_checked    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    issues          TEXT
);

CREATE TABLE IF NOT EXISTS policy_rules (
    policy_id    VARCHAR(100) PRIMARY KEY,
    rule_type    VARCHAR(50) NOT NULL,
    condition    JSONB NOT NULL,
    action       VARCHAR(200) NOT NULL,
    value        FLOAT,
    active       BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at   TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_workflow_instances_theme_slug
    ON workflow_instances(theme_slug);
CREATE INDEX IF NOT EXISTS idx_workflow_instances_status
    ON workflow_instances(status);
CREATE INDEX IF NOT EXISTS idx_supervisor_audit_log_created_at
    ON supervisor_audit_log(created_at DESC);

COMMIT;
