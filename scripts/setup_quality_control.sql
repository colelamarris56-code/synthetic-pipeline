-- Task validation rules
CREATE TABLE IF NOT EXISTS task_validation_rules (
    task_type VARCHAR(50) PRIMARY KEY,
    validation_rules JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- Task validation results
CREATE TABLE IF NOT EXISTS task_validations (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(50) REFERENCES agent_tasks(task_id),
    passed BOOLEAN NOT NULL,
    issues JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- Insert default validation rules
INSERT INTO task_validation_rules (task_type, validation_rules)
VALUES (
        'text_generation',
        '{
    "type": "str",
    "content": {
        "min_length": 10,
        "max_length": 50000,
        "banned_patterns": [
            "password\\s*=",
            "api_key\\s*=",
            "secret\\s*="
        ],
        "required_patterns": [
            "^[A-Za-z]",
            "[.!?]$"
        ]
    },
    "size": {
        "max_bytes": 1000000
    }
}'::jsonb
    ),
    (
        'code_generation',
        '{
    "type": "str",
    "content": {
        "min_length": 10,
        "max_length": 100000,
        "banned_patterns": [
            "exec\\s*\\(",
            "eval\\s*\\(",
            "subprocess\\.",
            "os\\.system"
        ]
    },
    "size": {
        "max_bytes": 2000000
    }
}'::jsonb
    ),
    (
        'data_validation',
        '{
    "type": "dict",
    "schema": {
        "valid": {
            "type": "bool",
            "required": true
        },
        "errors": {
            "type": "list",
            "required": false
        }
    }
}'::jsonb
    ) ON CONFLICT (task_type) DO NOTHING;