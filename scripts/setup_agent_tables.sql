-- Agent status tracking
CREATE TABLE IF NOT EXISTS agent_status (
    agent_id VARCHAR(50) PRIMARY KEY,
    status VARCHAR(20) NOT NULL,
    last_heartbeat TIMESTAMP NOT NULL,
    current_task_id VARCHAR(50),
    resource_usage JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- Agent task management
CREATE TABLE IF NOT EXISTS agent_tasks (
    task_id VARCHAR(50) PRIMARY KEY,
    agent_id VARCHAR(50) REFERENCES agent_status(agent_id),
    task_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    priority VARCHAR(10) NOT NULL,
    params JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error TEXT
);
-- Agent performance metrics
CREATE TABLE IF NOT EXISTS agent_metrics (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(50) REFERENCES agent_status(agent_id),
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metric_type VARCHAR(50) NOT NULL,
    value FLOAT NOT NULL,
    labels JSONB
);
-- Agent governance policies
CREATE TABLE IF NOT EXISTS agent_policies (
    policy_id VARCHAR(50) PRIMARY KEY,
    policy_type VARCHAR(50) NOT NULL,
    settings JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50) NOT NULL
);
-- Audit logging
CREATE TABLE IF NOT EXISTS agent_audit_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    agent_id VARCHAR(50) REFERENCES agent_status(agent_id),
    event_type VARCHAR(50) NOT NULL,
    details JSONB,
    correlation_id VARCHAR(50)
);
-- Insert default policies
INSERT INTO agent_policies (policy_id, policy_type, settings, created_by)
VALUES (
        'default-task-limits',
        'task_limits',
        '{"max_concurrent_tasks": 10, "task_timeout_minutes": 15, "rate_limit_rpm": 100, "default_priority": "medium"}'::jsonb,
        'system'
    ),
    (
        'default-resource-limits',
        'resource_limits',
        '{"cpu_percent": 50, "memory_gb": 8, "max_tokens_per_task": 2000, "daily_cost_limit": 100}'::jsonb,
        'system'
    ) ON CONFLICT (policy_id) DO NOTHING;