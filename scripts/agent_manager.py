"""Agent management module for controlling and monitoring AI agents."""

import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
import logging
from storage import FileStorage

logger = logging.getLogger(__name__)

# Initialize global storage
storage = FileStorage()

class AgentManager:
    """Manages AI agent lifecycle, tasks, and governance."""
    
    @staticmethod
    def get_active_agents() -> List[Dict[str, Any]]:
        """Get list of currently active agents and their status."""
        return storage.get_active_agents()

    @staticmethod
    def register_agent(agent_id: str) -> bool:
        """Register a new agent in the system."""
        return storage.register_agent(agent_id)
    
    @staticmethod
    def update_agent_status(agent_id: str, status: str) -> bool:
        """Update an agent's status."""
        return storage.update_agent_status(agent_id, status)
    
    @staticmethod
    def get_agent_metrics() -> Dict[str, Any]:
        """Get aggregated agent metrics."""
        return storage.get_agent_metrics()
    
    @staticmethod
    def add_task_result(agent_id: str, task_data: Dict[str, Any]) -> bool:
        """Record a task result."""
        return storage.add_task_result(agent_id, task_data)

    @staticmethod
    def get_agent_metrics(agent_id: str, metric_type: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get historical metrics for an agent."""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT timestamp, value, labels
                    FROM agent_metrics
                    WHERE agent_id = %s
                    AND metric_type = %s
                    AND timestamp > NOW() - INTERVAL '%s hours'
                    ORDER BY timestamp DESC
                """, (agent_id, metric_type, hours))
                return [dict(zip(['timestamp', 'value', 'labels'], row))
                        for row in cur.fetchall()]

    @staticmethod
    def get_policy(policy_type: str) -> Dict[str, Any]:
        """Get current policy settings."""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT settings
                    FROM agent_policies
                    WHERE policy_type = %s
                    ORDER BY updated_at DESC
                    LIMIT 1
                """, (policy_type,))
                result = cur.fetchone()
                return result[0] if result else {}

    @staticmethod
    def update_policy(policy_type: str, settings: Dict[str, Any], user: str) -> None:
        """Update policy settings."""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE agent_policies
                    SET settings = %s::jsonb,
                        updated_at = CURRENT_TIMESTAMP,
                        created_by = %s
                    WHERE policy_type = %s
                """, (json.dumps(settings), user, policy_type))
                
                # Log the policy update
                cur.execute("""
                    INSERT INTO agent_audit_log (event_type, details)
                    VALUES ('policy_updated', %s::jsonb)
                """, (json.dumps({
                    'policy_type': policy_type,
                    'new_settings': settings,
                    'updated_by': user
                }),))
                conn.commit()

    @staticmethod
    def get_audit_logs(hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit logs."""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT timestamp, agent_id, event_type, details
                    FROM agent_audit_log
                    WHERE timestamp > NOW() - INTERVAL '%s hours'
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (hours, limit))
                return [dict(zip(['timestamp', 'agent_id', 'event_type', 'details'], row))
                        for row in cur.fetchall()]

    @staticmethod
    def record_metric(agent_id: str, metric_type: str, value: float, 
                     labels: Optional[Dict[str, str]] = None) -> None:
        """Record a new metric measurement."""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO agent_metrics (agent_id, metric_type, value, labels)
                    VALUES (%s, %s, %s, %s::jsonb)
                """, (agent_id, metric_type, value, 
                      json.dumps(labels) if labels else None))
                conn.commit()

    @staticmethod
    def enforce_policies(agent_id: str) -> Dict[str, Any]:
        """Check and enforce all policies for an agent."""
        policies = {}
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get all policy types
                cur.execute("SELECT DISTINCT policy_type FROM agent_policies")
                for (policy_type,) in cur.fetchall():
                    cur.execute("""
                        SELECT settings
                        FROM agent_policies
                        WHERE policy_type = %s
                        ORDER BY updated_at DESC
                        LIMIT 1
                    """, (policy_type,))
                    settings = cur.fetchone()
                    if settings:
                        policies[policy_type] = settings[0]

        return policies