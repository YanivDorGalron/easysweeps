import csv
import subprocess
import argparse
from pathlib import Path
import click
import logging
from .config import config
from .utils import setup_logging
import wandb

logger = logging.getLogger(__name__)

def get_occupied_indices(sweep_id, gpu):
    """Get list of occupied agent indices for a specific sweep and GPU.
    
    Args:
        sweep_id (str): The sweep ID.
        gpu (int): The GPU index.
    Returns:
        set: A set of occupied agent indices. (Meaning the indices already in use, idx = 0,1,2,... and is a number representing the nth agent for this sweep on this GPU)
    """
    try:
        result = subprocess.run(['systemctl', '--user', 'list-units', '--type=scope', '--all'], 
                              capture_output=True, text=True)
        units = result.stdout.split('\n')
        occupied = set()
        prefix = f"wandb-agent-{sweep_id}-{gpu}-"
        for unit in units:
            if prefix in unit:
                parts = unit.split()
                if not parts:
                    continue
                unit_name = parts[0]
                if unit_name.startswith(prefix) and unit_name.endswith(".scope"):
                    try:
                        # Extract the index part: wandb-agent-{sweep_id}-{gpu}-{idx}.scope
                        idx_str = unit_name[len(prefix):-len(".scope")]
                        occupied.add(int(idx_str))
                    except ValueError:
                        continue
        return occupied
    except Exception as e:
        logger.error(f"Failed to get occupied indices: {e}")
        return set()

def launch_agents(args):
    """Launch wandb sweep agents for a specific sweep ID.
    
    This function launches Weights & Biases sweep agents using systemd scope units for a specific sweep ID
    across specified GPUs. It handles the following tasks:
    1. Sets up logging and creates necessary directories
    2. Verifies the sweep ID exists in the sweep log file
    3. Launches wandb agents with proper GPU assignments
    4. Uses systemd scope units for process management
    
    Args:
        args: An argparse.Namespace object containing:
            - sweep_log_dir: Directory containing the sweep log file
            - gpu_list: List of GPU indices to use
            - project: W&B project name
            - agents_per_sweep: Number of agents to launch per sweep
            - sweep_id: The sweep ID to launch agents for
    
    Raises:
        FileNotFoundError: If the sweep log file is not found
        Exception: For various errors during agent launch process
    
    Returns:
        None
    """
    # Set up logging
    log_dir = Path(config.get("agent_log_dir"))
    setup_logging(log_dir)

    agent_log_dir = Path(config.get("agent_log_dir"))
    agent_log_dir.mkdir(parents=True, exist_ok=True)

    # Find the sweep using W&B API
    try:
        api = wandb.Api()
        entity = config.get("entity")
        project = args.project

        # Get sweep info from W&B API
        sweep = api.sweep(f"{entity}/{project}/{args.sweep_id}")
        if not sweep:
            raise click.ClickException(f"No sweep found with ID: {args.sweep_id}")

        name = sweep.name
        sweep_id = args.sweep_id

    except Exception as e:
        logger.error(f"Failed to get sweep info from W&B API: {e}")
        raise

    # Launch agents on each specified GPU
    for gpu in args.gpu_list:
        # Get currently occupied indices for this sweep and GPU
        occupied = get_occupied_indices(sweep_id, gpu)
        
        # Launch multiple agents for this sweep on this GPU
        launched_count = 0
        current_idx = 0
        
        while launched_count < args.agents_per_sweep:
            # Skip if index is already taken
            if current_idx in occupied:
                current_idx += 1
                continue
                
            log_file = agent_log_dir / f"{name}_gpu{gpu}_agent{current_idx}.log"

            # Create the command
            cmd = (
                f'systemd-run --user --scope --unit=wandb-agent-{sweep_id}-{gpu}-{current_idx} bash -c "'
                f'trap \'pkill -P $$\' EXIT; '
                f'mkdir -p {agent_log_dir} && '
                f'CUDA_VISIBLE_DEVICES={gpu} PYTHONPATH=$PWD '
                f'exec wandb agent {config.get("entity")}/{args.project}/{sweep_id}" '
                f'>> {log_file} 2>&1 &'  # Added & to run in background
            )

            try:
                subprocess.run(cmd, shell=True)
                click.echo(f"Launched agent {current_idx} for {sweep_id}:{name} on GPU {gpu}")
                logger.debug(f"Launched agent {current_idx} for {name} on GPU {gpu}")
                launched_count += 1
            except Exception as e:
                logger.error(f"Failed to launch agent {current_idx}: {e}")
            
            current_idx += 1

