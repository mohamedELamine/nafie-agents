-- وكيل المنصة — migrations أولية
-- المرجع: agents/platform/docs/spec.md § ٤

CREATE TABLE IF NOT EXISTS theme_registry (
    theme_slug              VARCHAR(100) PRIMARY KEY,
    theme_name_ar           TEXT         NOT NULL,
    domain                  VARCHAR(50)  NOT NULL,
    cluster                 VARCHAR(50)  NOT NULL,
    wp_post_id              INTEGER      UNIQUE NOT NULL,
    wp_post_url             TEXT         NOT NULL,
    ls_product_id           VARCHAR(50)  UNIQUE NOT NULL,
    single_variant_id       VARCHAR(50)  NOT NULL,
    unlimited_variant_id    VARCHAR(50)  NOT NULL,
    current_version         VARCHAR(20)  NOT NULL,
    status                  VARCHAR(20)  NOT NULL DEFAULT 'published',
    published_at            TIMESTAMP    NOT NULL DEFAULT NOW(),
    last_updated_at         TIMESTAMP    NOT NULL DEFAULT NOW(),
    contract_version             VARCHAR(10),
    build_id                     VARCHAR(100),
    approved_event_id            VARCHAR(100),
    launch_idempotency_key       VARCHAR(200),
    last_update_event_id         VARCHAR(100),
    last_update_idempotency_key  VARCHAR(200)
);

CREATE TABLE IF NOT EXISTS vip_registry (
    id            SERIAL      PRIMARY KEY,
    ls_product_id VARCHAR(50) UNIQUE NOT NULL,
    ls_variant_id VARCHAR(50) UNIQUE NOT NULL,
    theme_slugs   TEXT[]      NOT NULL DEFAULT '{}',
    created_at    TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS inconsistent_states (
    record_id   VARCHAR(100) PRIMARY KEY,
    theme_slug  VARCHAR(100) NOT NULL,
    wp_state    VARCHAR(20)  NOT NULL,
    ls_state    VARCHAR(20)  NOT NULL,
    detected_at TIMESTAMP    NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMP,
    resolution  TEXT
);

CREATE TABLE IF NOT EXISTS execution_log (
    idempotency_key     VARCHAR(200) PRIMARY KEY,
    event_type          VARCHAR(50)  NOT NULL,
    theme_slug          VARCHAR(100) NOT NULL,
    version             VARCHAR(20)  NOT NULL,
    status              VARCHAR(30)  NOT NULL,
    started_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMP,
    last_completed_node VARCHAR(50),
    error_code          VARCHAR(50)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_theme_registry_status ON theme_registry(status);
CREATE INDEX IF NOT EXISTS idx_execution_log_theme ON execution_log(theme_slug);
CREATE INDEX IF NOT EXISTS idx_inconsistent_states_theme ON inconsistent_states(theme_slug, resolved_at);
