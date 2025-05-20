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
    """Launch wandb sweep agents with the given arguments.
    
    This function launches Weights & Biases sweep agents in tmux sessions across specified GPUs.
    It handles the following tasks:
    1. Sets up logging and creates necessary directories
    2. Reads sweep IDs from the sweep log file
    3. Creates tmux sessions and windows for each sweep
    4. Launches wandb agents with proper GPU assignments
    5. Logs all agent launches to a CSV file
    
    Args:
        args: An argparse.Namespace object containing:
            - sweep_log_dir: Directory containing the sweep log file
            - gpu_list: List of GPU indices to use
            - all_gpus: Boolean indicating whether to use all GPUs for each sweep
            - conda_env: Name of the conda environment to use
            - entity: W&B entity name
            - project: W&B project name
            - agents_per_sweep: Number of agents to launch per sweep
    
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

    try:
        with sweep_log.open() as f:
            lines = [line.strip() for line in f if line.strip()]
    except Exception as e:
        logger.error(f"Failed to read sweep log file: {e}")
        raise

    server = libtmux.Server()
    sweep_sessions = {}

    for i, line in enumerate(lines):
        try:
            name, sweep_id = line.split()
            
            # Determine which GPUs to use for this sweep
            if args.all_gpus:
                gpus_to_use = args.gpu_list  # Use all GPUs for each sweep
            else:
                gpu = args.gpu_list[i % len(args.gpu_list)]
                gpus_to_use = [gpu]  # Use one GPU per sweep

            for gpu in gpus_to_use:
                # Launch multiple agents for this sweep on this GPU
                for agent_idx in range(args.agents_per_sweep):
                    log_file = agent_log_dir / f"{name}_gpu{gpu}_agent{agent_idx}.log"

                    session_name = sweep_id
                    window_name = f"gpu{gpu}_agent{agent_idx}"

                    # Get or create session for the sweep_id
                    if session_name not in sweep_sessions:
                        # Kill existing session if needed
                        try:
                            existing = server.find_where({"session_name": session_name})
                            if existing:
                                click.echo(f"Killing existing session for sweep {sweep_id} on GPU {gpu}")
                                existing.kill_session()
                        except Exception as e:
                            logger.warning(f"Failed to kill existing session: {e}")

                        try:
                            session = server.new_session(session_name=session_name, kill_session=True, attach=False)
                            sweep_sessions[session_name] = session
                            logger.debug(f"Created new session for sweep {sweep_id} on GPU {gpu}")

                        except Exception as e:
                            logger.error(f"Failed to create new session: {e}")
                            continue
                    else:
                        session = sweep_sessions[session_name]

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
                            project_dir = copy_project_for_sweep(sweep_id, base_dir)
                            logger.info(f"Using project copy at {project_dir}")
                        except Exception as e:
                            logger.error(f"Failed to copy project for sweep {sweep_id}: {e}")
                            continue

                    # Create the command
                    conda_path = config.get("conda_path")
                    cmd = (
                        f"bash -c '"
                        f"echo \"Starting wandb agent {agent_idx} for sweep {sweep_id} on GPU {gpu}\" && "
                        f"cd {project_dir} && "  # Change to the project directory
                        f"source {conda_path} && "
                        f"echo \"Activating conda environment {args.conda_env}\" && "
                        f"conda activate {args.conda_env} && "
                        f"echo \"Setting CUDA_VISIBLE_DEVICES={gpu} and PYTHONPATH=$PWD\" && "
                        f"export CUDA_VISIBLE_DEVICES={gpu} && "
                        f"export PYTHONPATH=$PWD && "
                        f"echo \"Launching wandb agent for {args.entity}/{args.project}/{sweep_id}\" && "
                        f"wandb agent {args.entity}/{args.project}/{sweep_id} "
                        f"> {log_file} 2>&1'"
                    )

                    # Send the command to the pane
                    try:
                        pane = window.attached_pane
                        pane.send_keys(cmd)
                        click.echo(f"Launched agent for {session_name}:{name} on GPU {gpu}")
                        logger.debug(f"Launched agent for {name} in session '{session_name}', window '{window_name}' on GPU {gpu}")
                        launch_records.append([name, sweep_id, gpu, str(log_file)])
                    except Exception as e:
                        logger.error(f"Failed to send command to pane: {e}")
                        continue
        except Exception as e:
            logger.error(f"Failed to process sweep {i + 1}: {e}")
            continue
        click.echo('-'*100)

    # Write launch summary
    try:
        with launch_summary_file.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["sweep_name", "sweep_id", "gpu", "log_file"])
            writer.writerows(launch_records)
        click.echo(f"Wrote launch summary to {launch_summary_file}")
    except Exception as e:
        logger.error(f"Failed to write launch summary: {e}")
        raise
