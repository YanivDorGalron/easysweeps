import csv
import subprocess
import argparse
from pathlib import Path
import libtmux
import logging
from .config import config
from .utils import setup_logging

logger = logging.getLogger(__name__)

def launch_agents(args):
    """Launch wandb sweep agents with the given arguments"""
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
                log_file = agent_log_dir / f"{name}_gpu{gpu}.log"  # Modified to include GPU in log filename

                session_name = sweep_id  # Modified to include GPU in session name
                window_name = f"gpu{gpu}"

                # Get or create session for the sweep_id
                if session_name not in sweep_sessions:
                    # Kill existing session if needed
                    try:
                        existing = server.find_where({"session_name": session_name})
                        if existing:
                            logger.info(f"Killing existing session for sweep {sweep_id} on GPU {gpu}")
                            existing.kill_session()
                    except Exception as e:
                        logger.warning(f"Failed to kill existing session: {e}")

                    try:
                        session = server.new_session(session_name=session_name, kill_session=True, attach=False)
                        sweep_sessions[session_name] = session
                        logger.info(f"Created new session for sweep {sweep_id} on GPU {gpu}")

                    except Exception as e:
                        logger.error(f"Failed to create new session: {e}")
                        continue
                else:
                    session = sweep_sessions[session_name]

                # Create a new window for this agent
                try:
                    window = session.new_window(window_name=window_name)
                    logger.info(f"Created new window {window_name} for sweep {sweep_id}")
                except Exception as e:
                    logger.error(f"Failed to create new window: {e}")
                    continue

                # Create the command
                conda_path = config.get("conda_path")
                cmd = (
                    f"bash -c '"
                    f"echo \"Starting wandb agent for sweep {sweep_id} on GPU {gpu}\" && "
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
                    logger.info(f"Launched agent for {name} in session '{session_name}', window '{window_name}' on GPU {gpu}")
                    launch_records.append([name, sweep_id, gpu, str(log_file)])
                except Exception as e:
                    logger.error(f"Failed to send command to pane: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to process sweep {i + 1}: {e}")
            continue

    # Write launch summary
    try:
        with launch_summary_file.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["sweep_name", "sweep_id", "gpu", "log_file"])
            writer.writerows(launch_records)
        logger.info(f"Wrote launch summary to {launch_summary_file}")
    except Exception as e:
        logger.error(f"Failed to write launch summary: {e}")
        raise

