import csv
import subprocess
import argparse
from pathlib import Path
import click
import libtmux
import logging
from .config import config
from .utils import setup_logging, copy_project_for_sweep

logger = logging.getLogger(__name__)

def launch_agents(args):
    """Launch wandb sweep agents for a specific sweep ID.
    
    This function launches Weights & Biases sweep agents in tmux sessions for a specific sweep ID
    across specified GPUs. It handles the following tasks:
    1. Sets up logging and creates necessary directories
    2. Verifies the sweep ID exists in the sweep log file
    3. Creates tmux sessions and windows for the sweep
    4. Launches wandb agents with proper GPU assignments
    5. Logs all agent launches to a CSV file
    
    Args:
        args: An argparse.Namespace object containing:
            - sweep_log_dir: Directory containing the sweep log file
            - gpu_list: List of GPU indices to use
            - conda_env: Name of the conda environment to use
            - entity: W&B entity name
            - project: W&B project name
            - agents_per_sweep: Number of agents to launch per sweep
            - force_recopy: Boolean indicating whether to force recopy project directories
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

    sweep_log = Path(args.sweep_log_dir) / "created_sweeps.txt"
    if not sweep_log.exists():
        logger.error(f"Sweep log file not found: {sweep_log}")
        raise FileNotFoundError(f"Sweep log file not found: {sweep_log}")

    agent_log_dir = Path(config.get("agent_log_dir"))
    agent_log_dir.mkdir(parents=True, exist_ok=True)

    launch_summary_file = agent_log_dir / "agent_launches.csv"
    launch_records = []

    # Find the sweep in the log file
    try:
        with sweep_log.open() as f:
            sweep_info = None
            for line in f:
                if line.strip():
                    name, sweep_id = line.strip().split()
                    if sweep_id == args.sweep_id:
                        sweep_info = (name, sweep_id)
                        break
            
            if not sweep_info:
                raise click.ClickException(f"No sweep found with ID: {args.sweep_id}")
            
            name, sweep_id = sweep_info
    except Exception as e:
        logger.error(f"Failed to read sweep log file: {e}")
        raise

    server = libtmux.Server()
    session = server.find_where({"session_name": sweep_id})

    # Launch agents on each specified GPU
    for gpu in args.gpu_list:
        # Find the highest existing agent index for this sweep and GPU
        highest_agent_idx = -1
        if session:
            for window in session.windows:
                if window.name.startswith(f"gpu{gpu}_agent"):
                    try:
                        agent_num = int(window.name.split("_agent")[1])
                        highest_agent_idx = max(highest_agent_idx, agent_num)
                    except (ValueError, IndexError):
                        continue

        # Launch multiple agents for this sweep on this GPU
        for agent_idx in range(args.agents_per_sweep):
            # Calculate the actual agent index by adding to the highest existing index
            actual_agent_idx = highest_agent_idx + 1 + agent_idx
            log_file = agent_log_dir / f"{name}_gpu{gpu}_agent{actual_agent_idx}.log"
            window_name = f"gpu{gpu}_agent{actual_agent_idx}"

            # Get or create session for the sweep_id
            if session is None:
                click.echo(f"Creating first agent for sweep {sweep_id} on GPU {gpu}")
                try:
                    session = server.new_session(session_name=sweep_id, kill_session=True, attach=False)
                    logger.debug(f"Created new session for sweep {sweep_id} on GPU {gpu}")
                except Exception as e:
                    logger.error(f"Failed to create new session: {e}")
                    continue

            # Create a new window for this agent
            try:
                window = session.new_window(window_name=window_name)
                logger.debug(f"Created new window {window_name} for sweep {sweep_id}")
            except Exception as e:
                logger.error(f"Failed to create new window: {e}")
                continue

            # Handle project copying if enabled
            project_dir = Path.cwd()
            if config.get("enable_project_copy", False):
                try:
                    base_dir = Path(config.get("project_copy_base_dir"))
                    project_dir = copy_project_for_sweep(sweep_id, base_dir, force_recopy=getattr(args, 'force_recopy', False))
                    logger.debug(f"Using project copy at {project_dir}")
                except Exception as e:
                    logger.error(f"Failed to copy project for sweep {sweep_id}: {e}")
                    continue

            # Create the command
            conda_path = config.get("conda_path")
            cmd = (
                f'setsid bash -c \''
                f'trap "pkill -P $$" EXIT; '
                f'cd {project_dir} && '
                f'source {conda_path} && '
                f'conda activate {args.conda_env} && '
                f'mkdir -p {agent_log_dir} && '
                f'CUDA_VISIBLE_DEVICES={gpu} PYTHONPATH=$PWD '
                f'exec wandb agent {args.entity}/{args.project}/{sweep_id} '
                f'>> {log_file} 2>&1\''
            )

            # Send the command to the pane
            try:
                pane = window.attached_pane
                pane.send_keys(cmd)
                click.echo(f"Launched agent for {sweep_id}:{name} on GPU {gpu}")
                logger.debug(f"Launched agent for {name} in session '{sweep_id}', window '{window_name}' on GPU {gpu}")
                launch_records.append([name, sweep_id, gpu, str(log_file)])
            except Exception as e:
                logger.error(f"Failed to send command to pane: {e}")
                continue

    # Write launch summary
    try:
        mode = "a" if launch_summary_file.exists() else "w"
        with launch_summary_file.open(mode, newline="") as f:
            writer = csv.writer(f)
            if mode == "w":  # Only write header for new files
                writer.writerow(["sweep_name", "sweep_id", "gpu", "log_file"])
            writer.writerows(launch_records)
        click.echo(f"Wrote launch summary to {launch_summary_file}")
    except Exception as e:
        logger.error(f"Failed to write launch summary: {e}")
        raise
