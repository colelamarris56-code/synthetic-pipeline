# Agent Monitoring Dashboard

A real-time monitoring and management system for AI agents built with Streamlit.

## Features

- Real-time agent status monitoring
- Performance metrics visualization
- Task execution tracking
- Resource usage monitoring
- Auto-scaling capabilities

## Requirements

- Python 3.11+
- Streamlit
- psutil

## Installation

1. Clone the repository
```bash
git clone https://github.com/yourusername/synthetic-pipeline.git
cd synthetic-pipeline
```

2. Create a virtual environment and install dependencies
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

Run the monitoring dashboard:
```bash
streamlit run scripts/dashboard_app.py
```

Run the complete agent system:
```bash
python -m scripts.run
```

## Project Structure

- `scripts/` - Main application code
  - `dashboard_app.py` - Streamlit dashboard
  - `run.py` - Main entry point
  - `agent_process.py` - Agent implementation
  - `agent_manager.py` - Agent management system
  - `quality_control.py` - Quality control system
  - `storage.py` - Data storage layer
- `data/` - Storage for agent data and metrics