"""Main entry point to start the entire system."""

import subprocess
import sys
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def main():
    """Start all system components."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get script directory
    script_dir = Path(__file__).parent.resolve()
    
    try:
        # Start streamlit dashboard
        logger.info("Starting dashboard...")
        dashboard = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "scripts/dashboard_app.py"],
            cwd=script_dir.parent
        )
        
        # Start pipeline automation
        logger.info("Starting pipeline automation...")
        automation = subprocess.Popen(
            [sys.executable, "scripts/start_system.py"],
            cwd=script_dir.parent
        )
        
        # Start agent cluster
        logger.info("Starting agent cluster...")
        agents = subprocess.Popen(
            [sys.executable, "scripts/launch_agents.py", "--agents", "2"],
            cwd=script_dir.parent
        )
        
        logger.info("All components started")
        
        # Wait for all processes
        while True:
            if dashboard.poll() is not None:
                logger.error("Dashboard process died")
                break
            if automation.poll() is not None:
                logger.error("Automation process died")
                break
            if agents.poll() is not None:
                logger.error("Agent cluster process died")
                break
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        logger.info("Shutting down...")
        for process in [dashboard, automation, agents]:
            if process and process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
        logger.info("Shutdown complete")

if __name__ == "__main__":
    main()