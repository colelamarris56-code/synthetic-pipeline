"""AI Agent process that handles task execution and monitoring."""

import logging
import time
import json
import uuid
import psutil
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from contextlib import contextmanager

from agent_manager import AgentManager
from quality_control import QualityControl

logger = logging.getLogger(__name__)

class AIAgent:
    """AI Agent that executes tasks and self-monitors."""
    
    def __init__(self, agent_id: Optional[str] = None):
        self.agent_id = agent_id or str(uuid.uuid4())
        self.current_task: Optional[str] = None
        self.status = "initializing"
        self.last_heartbeat = datetime.now()
        self._register_agent()
    
    def _register_agent(self):
        """Register agent in the system."""
        AgentManager.register_agent(self.agent_id)
        self.status = "active"
                    self.status,
                    self.last_heartbeat,
                    json.dumps(self._get_resource_usage())
                ))
                conn.commit()
    
    def _get_resource_usage(self) -> Dict[str, float]:
        """Get current resource usage."""
        process = psutil.Process()
        return {
            'cpu_percent': process.cpu_percent(),
            'memory_percent': process.memory_percent(),
            'memory_mb': process.memory_info().rss / (1024 * 1024)
        }
    
    def _update_status(self, status: str):
        """Update agent status."""
        self.status = status
        self.last_heartbeat = datetime.now()
        self._register_agent()
    
    def _get_next_task(self) -> Optional[Dict[str, Any]]:
        """Get next task from queue."""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE agent_tasks
                    SET status = 'running',
                        agent_id = %s,
                        started_at = CURRENT_TIMESTAMP
                    WHERE task_id = (
                        SELECT task_id
                        FROM agent_tasks
                        WHERE status = 'pending'
                        ORDER BY priority DESC, created_at ASC
                        LIMIT 1
                        FOR UPDATE SKIP LOCKED
                    )
                    RETURNING task_id, task_type, params
                """, (self.agent_id,))
                conn.commit()
                
                result = cur.fetchone()
                if result:
                    return dict(zip(['task_id', 'task_type', 'params'], result))
                return None
    
    def _process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single task."""
        # Simulate task processing
        time.sleep(2)  # Replace with actual task processing
        
        # Generate sample output
        output = {
            'status': 'success',
            'message': f'Processed task {task["task_id"]}',
            'result': {'processed_at': datetime.now().isoformat()}
        }
        
        # Validate output
        passed, issues = QualityControl.validate_output(output, task['task_type'])
        if not passed:
            raise ValueError(f"Output validation failed: {issues}")
        
        return output
    
    def _complete_task(self, task_id: str, result: Dict[str, Any], error: Optional[str] = None):
        """Mark task as completed or failed."""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE agent_tasks
                    SET status = %s,
                        completed_at = CURRENT_TIMESTAMP,
                        result = %s,
                        error = %s
                    WHERE task_id = %s
                """, (
                    'completed' if error is None else 'failed',
                    json.dumps(result),
                    error,
                    task_id
                ))
                conn.commit()
    
    def run(self):
        """Main agent loop."""
        self._update_status('active')
        logger.info(f"Agent {self.agent_id} starting")
        
        try:
            while True:
                # Check policies
                policies = AgentManager.enforce_policies(self.agent_id)
                
                # Update heartbeat and resource usage
                self._register_agent()
                
                # Get next task
                task = self._get_next_task()
                if task:
                    logger.info(f"Processing task {task['task_id']}")
                    try:
                        result = self._process_task(task)
                        self._complete_task(task['task_id'], result)
                        logger.info(f"Completed task {task['task_id']}")
                    except Exception as e:
                        logger.error(f"Task {task['task_id']} failed: {str(e)}")
                        self._complete_task(task['task_id'], {}, str(e))
                else:
                    time.sleep(1)  # Wait for new tasks
                
        except Exception as e:
            logger.error(f"Agent {self.agent_id} failed: {str(e)}")
            self._update_status('error')
            raise
        finally:
            self._update_status('shutdown')

def main():
    """Start a new agent process."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    agent = AIAgent()
    agent.run()

if __name__ == "__main__":
    main()