"""File-based storage manager for agent data."""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class FileStorage:
    """Manages file-based storage for agent data."""
    
    def __init__(self, data_dir: str = "data"):
        """Initialize the file storage system."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.agents_file = self.data_dir / "agents.json"
        self.tasks_file = self.data_dir / "tasks.json"
        self.metrics_file = self.data_dir / "metrics.json"
        
        # Initialize storage files if they don't exist
        self._initialize_storage()
    
    def _initialize_storage(self):
        """Create storage files if they don't exist."""
        if not self.agents_file.exists():
            self._write_json(self.agents_file, [])
        if not self.tasks_file.exists():
            self._write_json(self.tasks_file, [])
        if not self.metrics_file.exists():
            self._write_json(self.metrics_file, [])
    
    def _read_json(self, file_path: Path) -> Any:
        """Read JSON data from a file."""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return []
    
    def _write_json(self, file_path: Path, data: Any):
        """Write JSON data to a file."""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error writing to {file_path}: {e}")
    
    def get_active_agents(self) -> List[Dict[str, Any]]:
        """Get list of currently active agents."""
        agents = self._read_json(self.agents_file)
        return [a for a in agents if a.get('status') == 'active']
    
    def register_agent(self, agent_id: str) -> bool:
        """Register a new agent in the system."""
        agents = self._read_json(self.agents_file)
        agent_data = {
            'agent_id': agent_id,
            'status': 'active',
            'registered_at': datetime.now().isoformat(),
            'last_heartbeat': datetime.now().isoformat(),
            'tasks_completed': 0,
            'success_rate': 100.0
        }
        agents.append(agent_data)
        self._write_json(self.agents_file, agents)
        return True
    
    def update_agent_status(self, agent_id: str, status: str) -> bool:
        """Update an agent's status."""
        agents = self._read_json(self.agents_file)
        for agent in agents:
            if agent['agent_id'] == agent_id:
                agent['status'] = status
                agent['last_heartbeat'] = datetime.now().isoformat()
                self._write_json(self.agents_file, agents)
                return True
        return False
    
    def get_agent_metrics(self) -> Dict[str, Any]:
        """Get aggregated agent metrics."""
        agents = self._read_json(self.agents_file)
        active_count = len([a for a in agents if a.get('status') == 'active'])
        total_tasks = sum(a.get('tasks_completed', 0) for a in agents)
        avg_success = sum(a.get('success_rate', 0) for a in agents) / len(agents) if agents else 0
        
        return {
            'active_agents': active_count,
            'total_tasks': total_tasks,
            'avg_success_rate': avg_success
        }
    
    def add_task_result(self, agent_id: str, task_data: Dict[str, Any]) -> bool:
        """Record a task result."""
        tasks = self._read_json(self.tasks_file)
        task_data['timestamp'] = datetime.now().isoformat()
        task_data['agent_id'] = agent_id
        tasks.append(task_data)
        self._write_json(self.tasks_file, tasks)
        
        # Update agent metrics
        agents = self._read_json(self.agents_file)
        for agent in agents:
            if agent['agent_id'] == agent_id:
                agent['tasks_completed'] += 1
                agent['last_heartbeat'] = datetime.now().isoformat()
                success_count = len([t for t in tasks if t['agent_id'] == agent_id and t.get('success', False)])
                total_count = len([t for t in tasks if t['agent_id'] == agent_id])
                agent['success_rate'] = (success_count / total_count * 100) if total_count > 0 else 100
                break
        self._write_json(self.agents_file, agents)
        return True