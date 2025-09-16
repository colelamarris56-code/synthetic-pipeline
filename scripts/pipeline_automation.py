"""Automated pipeline monitoring and scaling for AI agents."""

import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import logging
from concurrent.futures import ThreadPoolExecutor
from agent_manager import AgentManager, get_db_connection

logger = logging.getLogger(__name__)

class PipelineAutomation:
    """Handles automated monitoring, scaling, and error recovery for the agent pipeline."""
    
    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.running = False
        self._executor = ThreadPoolExecutor(max_workers=3)
    
    def start(self):
        """Start the automation monitoring loops."""
        self.running = True
        self._executor.submit(self._monitor_pipeline)
        self._executor.submit(self._scale_agents)
        self._executor.submit(self._recover_errors)
    
    def stop(self):
        """Stop all monitoring loops."""
        self.running = False
        self._executor.shutdown(wait=True)
    
    def _monitor_pipeline(self):
        """Monitor pipeline health and performance."""
        while self.running:
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        # Check task processing rates
                        cur.execute("""
                            SELECT 
                                COUNT(*) as total_tasks,
                                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                                AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration
                            FROM agent_tasks
                            WHERE created_at > NOW() - INTERVAL '1 hour'
                        """)
                        metrics = dict(zip(
                            ['total_tasks', 'completed', 'failed', 'avg_duration'],
                            cur.fetchone()
                        ))
                        
                        # Record monitoring metrics
                        AgentManager.record_metric(
                            'pipeline',
                            'task_completion_rate',
                            metrics['completed'] / metrics['total_tasks'] if metrics['total_tasks'] > 0 else 1.0,
                            {'window': '1h'}
                        )
                        
                        if metrics['failed'] > 0:
                            failure_rate = metrics['failed'] / metrics['total_tasks']
                            if failure_rate > 0.1:  # Over 10% failure rate
                                logger.warning(f"High failure rate detected: {failure_rate:.1%}")
                                self._handle_high_failure_rate()
                        
                        # Monitor resource usage
                        cur.execute("""
                            SELECT agent_id, resource_usage
                            FROM agent_status
                            WHERE last_heartbeat > NOW() - INTERVAL '5 minutes'
                        """)
                        for agent_id, usage in cur:
                            if usage and usage.get('cpu_percent', 0) > 80:
                                logger.warning(f"High CPU usage on {agent_id}: {usage['cpu_percent']}%")
                                self._handle_resource_pressure(agent_id, 'cpu')
            
            except Exception as e:
                logger.error(f"Pipeline monitoring error: {e}")
            
            time.sleep(self.check_interval)
    
    def _scale_agents(self):
        """Automatically scale agents based on workload."""
        while self.running:
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        # Get current workload metrics
                        cur.execute("""
                            SELECT 
                                COUNT(*) as pending_tasks,
                                (
                                    SELECT COUNT(*)
                                    FROM agent_status
                                    WHERE status = 'active'
                                    AND last_heartbeat > NOW() - INTERVAL '5 minutes'
                                ) as active_agents
                            FROM agent_tasks
                            WHERE status = 'pending'
                        """)
                        pending_tasks, active_agents = cur.fetchone()
                        
                        # Get task limits policy
                        task_limits = AgentManager.get_policy('task_limits')
                        max_tasks_per_agent = task_limits.get('max_concurrent_tasks', 10)
                        
                        # Calculate desired agent count
                        desired_agents = max(1, (pending_tasks + max_tasks_per_agent - 1) 
                                          // max_tasks_per_agent)
                        
                        if desired_agents > active_agents:
                            logger.info(f"Scaling up: {active_agents} → {desired_agents} agents")
                            self._scale_up(desired_agents - active_agents)
                        elif desired_agents < active_agents:
                            logger.info(f"Scaling down: {active_agents} → {desired_agents} agents")
                            self._scale_down(active_agents - desired_agents)
            
            except Exception as e:
                logger.error(f"Agent scaling error: {e}")
            
            time.sleep(self.check_interval * 5)  # Scale less frequently than monitoring
    
    def _recover_errors(self):
        """Automatically detect and recover from errors."""
        while self.running:
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        # Find failed tasks
                        cur.execute("""
                            SELECT task_id, agent_id, error, params
                            FROM agent_tasks
                            WHERE status = 'failed'
                            AND created_at > NOW() - INTERVAL '1 hour'
                            ORDER BY created_at DESC
                        """)
                        failed_tasks = cur.fetchall()
                        
                        for task_id, agent_id, error, params in failed_tasks:
                            if self._is_recoverable_error(error):
                                logger.info(f"Recovering task {task_id}")
                                self._retry_task(task_id, params)
                            else:
                                logger.warning(f"Unrecoverable error in task {task_id}: {error}")
                        
                        # Check for stuck tasks
                        cur.execute("""
                            SELECT task_id, agent_id
                            FROM agent_tasks
                            WHERE status = 'running'
                            AND started_at < NOW() - INTERVAL '30 minutes'
                        """)
                        for task_id, agent_id in cur.fetchall():
                            logger.warning(f"Found stuck task {task_id} on {agent_id}")
                            self._handle_stuck_task(task_id, agent_id)
            
            except Exception as e:
                logger.error(f"Error recovery error: {e}")
            
            time.sleep(self.check_interval)
    
    def _handle_high_failure_rate(self):
        """Handle high task failure rates."""
        # Log the incident
        AgentManager.record_metric('pipeline', 'high_failure_rate', 1.0)
        
        # Pause new task assignments
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE agent_status
                    SET status = 'paused'
                    WHERE status = 'active'
                """)
                conn.commit()
    
    def _handle_resource_pressure(self, agent_id: str, resource_type: str):
        """Handle resource pressure on an agent."""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if resource_type == 'cpu':
                    # Reduce concurrent tasks
                    cur.execute("""
                        UPDATE agent_status
                        SET status = 'throttled',
                            resource_usage = resource_usage || 
                                '{"max_concurrent_tasks": 2}'::jsonb
                        WHERE agent_id = %s
                    """, (agent_id,))
                conn.commit()
    
    def _scale_up(self, count: int):
        """Scale up the number of agents."""
        for _ in range(count):
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO agent_status (agent_id, status, last_heartbeat)
                        VALUES (gen_random_uuid(), 'initializing', CURRENT_TIMESTAMP)
                    """)
                    conn.commit()
    
    def _scale_down(self, count: int):
        """Scale down the number of agents."""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Find idle agents
                cur.execute("""
                    UPDATE agent_status
                    SET status = 'shutdown'
                    WHERE agent_id IN (
                        SELECT a.agent_id
                        FROM agent_status a
                        LEFT JOIN agent_tasks t ON 
                            a.agent_id = t.agent_id AND 
                            t.status = 'running'
                        WHERE t.task_id IS NULL
                        AND a.status = 'active'
                        LIMIT %s
                    )
                """, (count,))
                conn.commit()
    
    def _is_recoverable_error(self, error: str) -> bool:
        """Check if an error is recoverable."""
        recoverable_patterns = [
            'timeout',
            'connection reset',
            'temporary failure',
            'rate limit'
        ]
        return any(pattern in error.lower() for pattern in recoverable_patterns)
    
    def _retry_task(self, task_id: str, params: Dict[str, Any]):
        """Retry a failed task."""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Mark original as retried
                cur.execute("""
                    UPDATE agent_tasks
                    SET status = 'retried'
                    WHERE task_id = %s
                """, (task_id,))
                
                # Create new task
                cur.execute("""
                    INSERT INTO agent_tasks (
                        task_id, task_type, status, priority, params
                    )
                    SELECT
                        gen_random_uuid(),
                        task_type,
                        'pending',
                        priority,
                        params
                    FROM agent_tasks
                    WHERE task_id = %s
                """, (task_id,))
                conn.commit()
    
    def _handle_stuck_task(self, task_id: str, agent_id: str):
        """Handle a stuck task."""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Mark task as failed
                cur.execute("""
                    UPDATE agent_tasks
                    SET status = 'failed',
                        error = 'Task stuck for over 30 minutes'
                    WHERE task_id = %s
                """, (task_id,))
                
                # Reset agent status
                cur.execute("""
                    UPDATE agent_status
                    SET status = 'active',
                        current_task_id = NULL
                    WHERE agent_id = %s
                """, (agent_id,))
                conn.commit()
        
        # Try to recover the task
        self._retry_task(task_id, {})