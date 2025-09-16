"""Launch script for the agent monitoring and automation system."""

import logging
import streamlit as st
from pipeline_automation import PipelineAutomation
from agent_manager import AgentManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Start the agent monitoring and automation system."""
    try:
        logger.info("Starting pipeline automation...")
        pipeline = PipelineAutomation()
        pipeline.start()
        
        logger.info("Checking initial agent status...")
        active_agents = AgentManager.get_active_agents()
        logger.info(f"Found {len(active_agents)} active agents")
        
        logger.info("Loading policy configuration...")
        task_limits = AgentManager.get_policy('task_limits')
        resource_limits = AgentManager.get_policy('resource_limits')
        logger.info("Policy configuration loaded")
        
        logger.info("System startup complete")
        
    except Exception as e:
        logger.error(f"Failed to start system: {str(e)}")
        raise

if __name__ == "__main__":
    main()