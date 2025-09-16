"""Script to launch and manage multiple AI agents."""

import argparse
import logging
import multiprocessing
import signal
import sys
import time
from typing import List
import psutil

from agent_process import AIAgent
from agent_manager import AgentManager

logger = logging.getLogger(__name__)

class AgentCluster:
    """Manages a cluster of AI agents."""
    
    def __init__(self, initial_count: int = 2):
        self.initial_count = initial_count
        self.processes: List[multiprocessing.Process] = []
        self.running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)
    
    def start_agent(self):
        """Start a new agent process."""
        process = multiprocessing.Process(target=AIAgent().run)
        process.start()
        self.processes.append(process)
        logger.info(f"Started agent process {process.pid}")
    
    def stop_agent(self, process: multiprocessing.Process):
        """Stop an agent process."""
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
        self.processes.remove(process)
        logger.info(f"Stopped agent process {process.pid}")
    
    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Received shutdown signal")
        self.running = False
    
    def monitor_agents(self):
        """Monitor agent processes and restart if needed."""
        while self.running:
            # Check each process
            for process in self.processes[:]:
                if not process.is_alive():
                    logger.warning(f"Agent process {process.pid} died, restarting")
                    self.stop_agent(process)
                    self.start_agent()
            
            # Check system resources
            if psutil.cpu_percent() > 90 or psutil.virtual_memory().percent > 90:
                logger.warning("System resources critical, stopping one agent")
                if self.processes:
                    self.stop_agent(self.processes[-1])
            
            time.sleep(5)
    
    def run(self):
        """Run the agent cluster."""
        logger.info(f"Starting agent cluster with {self.initial_count} agents")
        
        # Start initial agents
        for _ in range(self.initial_count):
            self.start_agent()
        
        try:
            self.monitor_agents()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            logger.info("Shutting down agent cluster")
            for process in self.processes:
                self.stop_agent(process)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Launch AI agent cluster")
    parser.add_argument(
        "--agents",
        type=int,
        default=2,
        help="Number of agents to start"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level"
    )
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    cluster = AgentCluster(initial_count=args.agents)
    cluster.run()

if __name__ == "__main__":
    main()