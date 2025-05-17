# Weights & Biases Sweep Automation

This project provides a set of tools to automate the creation, management, and monitoring of Weights & Biases (wandb) hyperparameter sweeps. It's particularly useful for running large-scale hyperparameter optimization experiments across multiple GPUs.

## Why This Project?

When running multiple hyperparameter sweeps across different GPUs, managing the creation, launching, and cleanup of sweep agents can become tedious and error-prone. This project automates these tasks, providing:

- Automated sweep creation from templates
- Distributed agent launching across multiple GPUs
- Centralized logging and monitoring
- Easy cleanup of running agents

## Features

- **Automated Sweep Creation**: Create multiple sweeps from a template with different parameter combinations
- **GPU Management**: Automatically distribute sweep agents across available GPUs
- **Logging**: Centralized logging of all sweep agents
- **Cleanup**: Easy termination of running agents with optional log cleanup

## Prerequisites

- Python 3.x
- Weights & Biases CLI (`wandb`)
- Conda environment with required dependencies
- Multiple GPUs (optional, but recommended for parallel execution)

## Project Structure

```
wandb_sweep_automation/
├── launch_sweeps.py    # Creates sweeps from templates
├── launch_agents.py    # Launches sweep agents across GPUs
├── kill_agents.py      # Terminates running sweep agents
└── sweeps/            # Directory containing sweep templates and logs
```

## Usage

### 1. Creating Sweeps

First, create your sweep template in YAML format and place it in the `sweeps` directory. Then run:

```bash
python launch_sweeps.py
```

This will:
- Create sweeps based on your template and parameter combinations
- Save sweep configurations as YAML files
- Create the sweeps in wandb
- Log created sweep IDs to `sweeps/created_sweeps.txt`

### 2. Launching Agents

To launch agents for all created sweeps:

```bash
python launch_agents.py
```

This will:
- Distribute agents across available GPUs
- Create log files for each agent
- Save launch information to `agent_logs/agent_launches.csv`

### 3. Cleaning Up

To terminate all running sweep agents:

```bash
python kill_agents.py
```

This will:
- Find and terminate all running sweep agents
- Optionally clean up log files
- Update the launch records CSV

## Configuration

### GPU Configuration

Edit `launch_agents.py` to configure:
- Available GPUs (`gpu_list`)
- Wandb entity and project names
- Log directory location

### Sweep Configuration

Edit `launch_sweeps.py` to configure:
- Search space parameters
- Sweep template location
- Output directory structure

## Example

1. Create a sweep template (`sweeps/sweep_template.yaml`):
```yaml
name: "my-sweep-{num_layers}-{dataset}"
method: "grid"
parameters:
  num_layers:
    value: 16
  dataset:
    value: "IMDBBINARY"
```

2. Run the automation:
```bash
# Create sweeps
python launch_sweeps.py

# Launch agents
python launch_agents.py

# When done, clean up
python kill_agents.py
```

## Notes

- Make sure your wandb CLI is properly configured with your credentials
- The project assumes a conda environment named 'pool' - modify the environment name in `launch_agents.py` if needed
- Log files are stored in the `agent_logs` directory for monitoring
- The project automatically handles GPU distribution to maximize resource utilization 