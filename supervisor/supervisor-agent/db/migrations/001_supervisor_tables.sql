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
