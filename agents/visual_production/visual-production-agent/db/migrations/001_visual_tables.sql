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
