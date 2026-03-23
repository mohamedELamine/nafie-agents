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
