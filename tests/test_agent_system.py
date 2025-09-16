"""Tests for agent monitoring, governance, and automation systems."""

import pytest
import json
from datetime import datetime, timedelta
import uuid
from scripts.agent_manager import AgentManager
from scripts.pipeline_automation import PipelineAutomation
from scripts.quality_control import QualityControl

@pytest.fixture
def db_connection(pg):
    """Create test database connection."""
    with pg() as conn:
        yield conn

@pytest.fixture
def setup_test_data(db_connection):
    """Set up test data in the database."""
    with db_connection.cursor() as cur:
        # Create test agents
        cur.execute("""
            INSERT INTO agent_status (agent_id, status, last_heartbeat)
            VALUES 
                ('test-agent-1', 'active', CURRENT_TIMESTAMP),
                ('test-agent-2', 'active', CURRENT_TIMESTAMP)
            ON CONFLICT (agent_id) DO NOTHING
        """)
        
        # Create test tasks
        cur.execute("""
            INSERT INTO agent_tasks (
                task_id, agent_id, task_type, status, priority, 
                created_at, started_at, completed_at
            )
            VALUES 
                ('task-1', 'test-agent-1', 'test', 'completed', 'medium',
                 CURRENT_TIMESTAMP - INTERVAL '1 hour',
                 CURRENT_TIMESTAMP - INTERVAL '1 hour',
                 CURRENT_TIMESTAMP - INTERVAL '30 minutes'),
                ('task-2', 'test-agent-2', 'test', 'running', 'high',
                 CURRENT_TIMESTAMP - INTERVAL '30 minutes',
                 CURRENT_TIMESTAMP - INTERVAL '30 minutes',
                 NULL)
            ON CONFLICT (task_id) DO NOTHING
        """)
        
        # Add test policies
        cur.execute("""
            INSERT INTO agent_policies (policy_id, policy_type, settings, created_by)
            VALUES 
                ('test-task-limits', 'task_limits',
                 '{"max_concurrent_tasks": 5, "task_timeout_minutes": 10}'::jsonb,
                 'test'),
                ('test-resource-limits', 'resource_limits',
                 '{"cpu_percent": 50, "memory_gb": 4}'::jsonb,
                 'test')
            ON CONFLICT (policy_id) DO NOTHING
        """)
        
        db_connection.commit()

class TestAgentManager:
    """Test agent management functionality."""
    
    def test_get_active_agents(self, setup_test_data):
        """Test retrieving active agents."""
        agents = AgentManager.get_active_agents()
        assert len(agents) >= 2
        assert any(a['agent_id'] == 'test-agent-1' for a in agents)
        assert any(a['agent_id'] == 'test-agent-2' for a in agents)
        
    def test_get_policy(self, setup_test_data):
        """Test retrieving policy settings."""
        task_limits = AgentManager.get_policy('task_limits')
        assert task_limits['max_concurrent_tasks'] == 5
        assert task_limits['task_timeout_minutes'] == 10
        
    def test_update_policy(self, setup_test_data, db_connection):
        """Test updating policy settings."""
        new_settings = {
            'max_concurrent_tasks': 8,
            'task_timeout_minutes': 15
        }
        AgentManager.update_policy('task_limits', new_settings, 'test')
        
        # Verify update
        updated = AgentManager.get_policy('task_limits')
        assert updated['max_concurrent_tasks'] == 8
        assert updated['task_timeout_minutes'] == 15
        
    def test_record_metric(self, setup_test_data, db_connection):
        """Test recording agent metrics."""
        AgentManager.record_metric(
            'test-agent-1',
            'cpu_usage',
            75.5,
            {'type': 'system'}
        )
        
        # Verify metric was recorded
        with db_connection.cursor() as cur:
            cur.execute("""
                SELECT value, labels
                FROM agent_metrics
                WHERE agent_id = 'test-agent-1'
                AND metric_type = 'cpu_usage'
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            value, labels = cur.fetchone()
            assert value == 75.5
            assert labels['type'] == 'system'

class TestPipelineAutomation:
    """Test pipeline automation functionality."""
    
    def test_error_recovery(self, setup_test_data, db_connection):
        """Test error recovery mechanism."""
        pipeline = PipelineAutomation(check_interval=1)
        
        # Create a failed task
        with db_connection.cursor() as cur:
            cur.execute("""
                INSERT INTO agent_tasks (
                    task_id, task_type, status, priority, error
                )
                VALUES (
                    'failed-task-1',
                    'test',
                    'failed',
                    'medium',
                    'connection timeout'
                )
            """)
            db_connection.commit()
        
        # Run recovery
        pipeline._recover_errors()
        
        # Verify task was retried
        with db_connection.cursor() as cur:
            cur.execute("""
                SELECT status
                FROM agent_tasks
                WHERE task_id = 'failed-task-1'
            """)
            status = cur.fetchone()[0]
            assert status == 'retried'
    
    def test_scale_up(self, setup_test_data, db_connection):
        """Test agent scaling up."""
        pipeline = PipelineAutomation(check_interval=1)
        
        # Add pending tasks
        with db_connection.cursor() as cur:
            for i in range(20):
                cur.execute("""
                    INSERT INTO agent_tasks (
                        task_id, task_type, status, priority
                    )
                    VALUES (
                        %s,
                        'test',
                        'pending',
                        'medium'
                    )
                """, (f'pending-task-{i}',))
            db_connection.commit()
        
        # Run scaling
        pipeline._scale_agents()
        
        # Verify new agents were added
        with db_connection.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM agent_status WHERE status = 'initializing'")
            count = cur.fetchone()[0]
            assert count > 0

class TestQualityControl:
    """Test quality control functionality."""
    
    def test_validate_output_schema(self):
        """Test output schema validation."""
        output = {
            'status': 'success',
            'message': 'Test completed'
        }
        
        validation_rules = {
            'type': 'dict',
            'schema': {
                'status': {
                    'type': 'str',
                    'required': True,
                    'enum': ['success', 'error']
                },
                'message': {
                    'type': 'str',
                    'required': True
                }
            }
        }
        
        passed, issues = QualityControl.validate_output(
            output,
            'test',
            validation_rules
        )
        assert passed
        assert not issues
    
    def test_validate_content_safety(self):
        """Test content safety validation."""
        output = "This is a test output with password=secret123"
        
        validation_rules = {
            'type': 'str',
            'content': {
                'banned_patterns': [
                    r'password\s*=',
                    r'api_key\s*='
                ]
            }
        }
        
        passed, issues = QualityControl.validate_output(
            output,
            'test',
            validation_rules
        )
        assert not passed
        assert any('banned pattern' in issue for issue in issues)
    
    def test_size_limits(self):
        """Test size limit validation."""
        large_output = "x" * 6000000  # 6MB
        
        validation_rules = {
            'type': 'str',
            'size': {
                'max_bytes': 5000000  # 5MB
            }
        }
        
        passed, issues = QualityControl.validate_output(
            large_output,
            'test',
            validation_rules
        )
        assert not passed
        assert any('too large' in issue for issue in issues)