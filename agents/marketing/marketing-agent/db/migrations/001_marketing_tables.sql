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