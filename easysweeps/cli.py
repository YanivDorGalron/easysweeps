from typing_extensions import deprecated
import click
import time
from pathlib import Path
import libtmux
from . import launch_agents
from . import launch_sweeps
import yaml
import logging
from .config import config
from .utils import setup_logging, send_ctrl_c, send_ctrl_c_window
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.shortcuts import radiolist_dialog

logger = logging.getLogger(__name__)

@click.group()
def cli():
    """EasySweeps - A powerful CLI tool for automating Weights & Biases sweep creation and management.

    This tool helps you create and manage multiple wandb sweeps efficiently by:
    - Creating multiple sweeps from a template and search space configuration
    - Launching sweep agents in tmux sessions for better process management
    - Managing GPU resources across multiple sweeps
    - Providing comprehensive logging and monitoring

    For detailed help on each command, use: easysweeps COMMAND --help
    """
    # Set up logging
    log_dir = Path(config.get("agent_log_dir"))
    setup_logging(log_dir)

@cli.command()
@click.option('--sweep-dir', type=click.Path(), help='Directory containing sweep configurations (default: from config.yaml)')
@click.option('--template', type=click.Path(), help='Sweep template file (default: sweep_dir/sweep_template.yaml)')
@click.option('--variants', type=click.Path(), help='Sweep variants configuration file (default: sweep_dir/sweep_variants.yaml)')
def sweep(sweep_dir, template, variants):
    """Create and launch wandb sweeps from a template and variants configuration.

    This command creates multiple wandb sweeps by combining a template configuration
    with a variants definition. The template defines the sweep structure while
    the variants file specifies the different parameter combinations to create sweeps for.

    Example:
        easysweeps sweep --sweep-dir sweeps/ --template sweeps/sweep_template.yaml --variants sweeps/sweep_variants.yaml
    """
    try:
        # Use provided paths or defaults from config
        sweep_dir = Path(sweep_dir or config.get("sweep_dir"))
        template = template or (sweep_dir / "sweep_template.yaml")
        variants = variants or (sweep_dir / "sweep_variants.yaml")

        # Validate files exist
        if not template.exists():
            raise click.ClickException(f"Template file not found: {template}")
        if not variants.exists():
            raise click.ClickException(f"Variants file not found: {variants}")

        # Create sweeps
        created_sweeps = launch_sweeps.create_sweeps(
            sweep_dir=sweep_dir,
            template_file=template,
            variants_file=variants
        )
        
        click.echo(f"Successfully created {len(created_sweeps)} sweeps")
        
    except Exception as e:
        logger.error(f"Failed to create sweeps: {e}")
        raise click.ClickException(str(e))

@cli.command()
@click.argument('sweep_id', required=False)
@click.option('--gpu-list', required=True, help='Comma-separated list of GPU indices to use (e.g., "0,1,2")')
@click.option('--agents-per-sweep', type=int, default=1, help='Number of agents to launch per sweep on each GPU')
@click.option('--force-recopy', is_flag=True, help='Force recopy project directories even if they already exist')
def agent(sweep_id, gpu_list, agents_per_sweep, force_recopy):
    """Launch wandb sweep agents for a specific sweep ID on specified GPUs.

    This command launches wandb sweep agents in tmux sessions for a specific sweep ID,
    distributing them across the specified GPUs. Each agent runs in its own tmux window
    for better process management and monitoring.

    If no sweep ID is provided, it will display all available sweeps.

    The command uses the following configuration from config.yaml:
    - conda_env: The conda environment to use
    - entity: The wandb entity name
    - project: The wandb project name
    - sweep_dir: Directory containing sweep configurations

    Example:
        easysweeps agent abc123 --gpu-list 0,1,2  # Launch agents for sweep abc123 on GPUs 0,1,2
        easysweeps agent abc123 --gpu-list 0 --agents-per-sweep 3  # Launch 3 agents on GPU 0
        easysweeps agent --gpu-list 0,1  # Show all available sweeps
    """
    try:
        # Parse GPU list
        try:
            gpu_list = [int(gpu.strip()) for gpu in gpu_list.split(',')]
        except ValueError:
            raise click.ClickException("GPU list must be comma-separated integers (e.g., '0,1,2')")

        # If no sweep_id provided, show all available sweeps
        if not sweep_id:
            sweep_log = Path(config.get("sweep_dir")) / "created_sweeps.txt"
            if not sweep_log.exists():
                raise click.ClickException("No sweep log file found. Have you created any sweeps?")

            click.echo("\nAvailable sweeps:")
            click.echo("-" * 50)
            with sweep_log.open() as f:
                for line in f:
                    if line.strip():
                        name, sid = line.strip().split()
                        click.echo(f"Name: {name}, ID: {sid}")
                        click.echo("-" * 50)
            return

        # Use provided values or defaults from config
        args = type('Args', (), {
            'conda_env': config.get("conda_env"),
            'sweep_log_dir': config.get("sweep_dir"),
            'gpu_list': gpu_list,
            'entity': config.get("entity"),
            'project': config.get("project"),
            'all_gpus': True,  # Always use all specified GPUs
            'agents_per_sweep': agents_per_sweep,
            'force_recopy': force_recopy,
            'sweep_id': sweep_id
        })

        # Run the agent launch
        launch_agents.launch_agents(args)
        click.echo("Successfully launched sweep agents")
        
    except Exception as e:
        logger.error(f"Failed to launch agents: {e}")
        raise click.ClickException(str(e))

def get_sweep_ids():
    """Get list of sweep IDs from the log file"""
    try:
        sweep_log = Path(config.get("sweep_dir")) / "created_sweeps.txt"
        if not sweep_log.exists():
            return []
        
        with sweep_log.open() as f:
            sweep_ids = [line.strip().split()[1] for line in f if line.strip()]
        
        return sweep_ids
    except Exception as e:
        logger.error(f"Failed to get sweep IDs: {e}")
        return []

@deprecated("Use kill_all instead")
@cli.command()
@click.argument('sweep_id', required=False)
@click.option('--gpu', type=int, required=True, help='GPU number to kill the agent from')
@click.option('--agent', type=int, help='Specific agent number to kill (if multiple agents per GPU)')
def kill(sweep_id, gpu, agent):
    """Kill a specific wandb sweep agent running on a specific GPU.

    This command kills a wandb sweep agent that is running in a tmux session
    on the specified GPU. The sweep_id should match the session name, and the
    GPU number should match the window name (e.g., "gpu0_agent0").

    If --agent is not specified, all agents for the sweep on the specified GPU will be killed.

    Example:
        easysweeps kill abc123 --gpu 0  # Kills all agents for sweep abc123 on GPU 0
        easysweeps kill abc123 --gpu 0 --agent 1  # Kills only agent 1 for sweep abc123 on GPU 0
    """
    raise click.ClickException("This command is deprecated. Please use kill_all instead.")
    try:
        # Get all sweep IDs
        sweep_ids = get_sweep_ids()
        if not sweep_ids:
            raise click.ClickException("No sweep IDs found in the log file")

        # If no sweep_id provided or partial match, show selection dialog
        if not sweep_id:
            sweep_id = prompt('Enter partial sweep ID: ', completer=WordCompleter(sweep_ids))
        
        # Filter sweep IDs that match the input
        matching_sweeps = [sid for sid in sweep_ids if sid.startswith(sweep_id)]
        
        if not matching_sweeps:
            raise click.ClickException(f"No sweep IDs found matching '{sweep_id}'")
        
        # If multiple matches, show selection dialog
        if len(matching_sweeps) > 1:
            sweep_id = radiolist_dialog(
                title="Select sweep ID",
                text="Multiple matches found. Please select one:",
                values=[(sid, sid) for sid in matching_sweeps]
            ).run()
            
            if not sweep_id:  # User cancelled
                return

        # Now proceed with killing the selected sweep
        server = libtmux.Server()
        
        session = server.find_where({"session_name": sweep_id})
        if not session:
            raise click.ClickException(f"No session found for sweep ID: {sweep_id}")

        if agent is not None:
            window_name = f"gpu{gpu}_agent{agent}"
            window = session.find_where({"window_name": window_name})
            if window:
                send_ctrl_c_window(window)
                time.sleep(2)
                window.kill()
                click.echo(f"Killed agent {agent} for sweep {sweep_id} on GPU {gpu}")
            else:
                raise click.ClickException(f"No agent {agent} found for sweep {sweep_id} on GPU {gpu}")
        else:
            # Kill all agents on this GPU
            windows = session.windows
            killed = False
            for window in windows:
                if window.name.startswith(f"gpu{gpu}_agent"):
                    send_ctrl_c_window(window)
                    time.sleep(2)
                    window.kill()
                    killed = True
            if killed:
                click.echo(f"Killed all agents for sweep {sweep_id} on GPU {gpu}")
            else:
                raise click.ClickException(f"No agents found for sweep {sweep_id} on GPU {gpu}")

        # Check if this was the last window in the session
        remaining_windows = session.windows
        if len(remaining_windows) == 1: # default window
            send_ctrl_c(session)
            time.sleep(2)
            session.kill()
            click.echo(f"No more agents running for{sweep_id}")
            
    except Exception as e:
        logger.error(f"Failed to kill agent: {e}")
        raise click.ClickException(str(e))
    
@cli.command()
def status():
    """Show status of all sweeps and running agents in a pretty format.
    
    This command displays:
    - All created sweeps from the sweep log
    - Currently running agents in tmux sessions and windows
    - GPU assignments for each agent
    - Status of each agent (running/stopped)
    """
    try:
        # Get all sweep IDs and names
        sweep_log = Path(config.get("sweep_dir")) / "created_sweeps.txt"
        if not sweep_log.exists():
            raise click.ClickException("No sweep log file found. Have you created any sweeps?")

        sweeps = []
        with sweep_log.open() as f:
            for line in f:
                if line.strip():
                    name, sweep_id = line.strip().split()
                    sweeps.append((name, sweep_id))

        # Get running sessions
        server = libtmux.Server()
        sessions = server.sessions

        # Create a pretty table
        click.echo("=== Sweeps and Agents Status ===\n")
        
        for name, sweep_id in sweeps:
            click.echo(f"Sweep: {name} (ID: {sweep_id})")
            
            # Find running agents for this sweep
            running_agents = []
            for session in sessions:
                if session.name.startswith(sweep_id):
                    # Get all windows in this session
                    windows = session.windows
                    for window in windows:
                        if window.name.startswith('gpu'):
                            # Parse GPU and agent numbers from window name
                            parts = window.name.split('_')
                            gpu = parts[0].replace('gpu', '')
                            agent = parts[1].replace('agent', '') if len(parts) > 1 else '0'
                            
                            # Check if the window has a running process
                            pane = window.attached_pane
                            if pane and pane.pane_pid:
                                running_agents.append((gpu, agent, "running"))
                            else:
                                running_agents.append((gpu, agent, "stopped"))
            
            if running_agents:
                click.echo("Agents:")
                for gpu, agent, status in sorted(running_agents, key=lambda x: (int(x[0]), int(x[1]))):
                    status_color = "green" if status == "running" else "red"
                    click.echo(f"  GPU {gpu}, Agent {agent}: {click.style(status, fg=status_color)}")
            else:
                click.echo("No agents currently running")
            
            click.echo("-" * 50)

        if not sweeps:
            click.echo("No sweeps found in the log file")
            
    except Exception as e:
        logger.error(f"Failed to show status: {e}")
        raise click.ClickException(str(e))
    
@cli.command()
@click.option('--force', is_flag=True, help='Force kill without confirmation')
@click.option('--gpu', type=str, help='Kill all processes on a specific GPU using nvidia-smi')
@click.option('--server', is_flag=True, help='Kill all wandb processes on the server using pkill')
def kill_all(force, gpu=None, server=False):
    """Kill sweep agents.
    
    This command will:
    - Find all sweep sessions from your sweep log
    - Kill sweep agents in those sessions (optionally on a specific GPU)
    - Clean up the tmux sessions
    
    Additional options:
    - Use --kill-all-gpu to kill all processes on a specific GPU using nvidia-smi
    - Use --kill-all-server to kill all wandb processes on the server using pkill
    
    Use the --force flag to skip confirmation.
    """
    try:
        # Handle kill-all-server option
        if server:
            if not force and not click.confirm("This will kill ALL wandb processes on the server. Continue?"):
                return
            import subprocess
            # Use pkill with -P to kill parent and child processes
            subprocess.run(['pkill', '-f', 'wandb'])
            click.echo("Killed all wandb processes on the server")
            return
        # Handle kill-all-gpu option
        elif gpu:
            if not force and not click.confirm(f"This will kill ALL processes on GPU {gpu}. Continue?"):
                return
            import subprocess
            # Get processes on the GPU
            result = subprocess.run(['nvidia-smi', '-i', gpu, '--query-compute-apps=pid', '--format=csv,noheader'], 
                                  capture_output=True, text=True)
            pids = [pid.strip() for pid in result.stdout.split('\n') if pid.strip()]
            
            # Kill each process and its children
            for pid in pids:
                try:
                    # Get child processes
                    child_result = subprocess.run(['pgrep', '-P', pid], capture_output=True, text=True)
                    child_pids = [cp.strip() for cp in child_result.stdout.split('\n') if cp.strip()]
                    
                    # Kill children first
                    for child_pid in child_pids:
                        subprocess.run(['kill', '-9', child_pid])
                    
                    # Kill the main process
                    subprocess.run(['kill', '-9', pid])
                    
                    # Try to kill parent process if it exists
                    try:
                        parent_pid = subprocess.run(['ps', '-o', 'ppid=', '-p', pid], 
                                                  capture_output=True, text=True).stdout.strip()
                        if parent_pid and parent_pid != '1':  # Don't kill init process
                            subprocess.run(['kill', '-9', parent_pid])
                    except Exception as e:
                        logger.warning(f"Could not kill parent process for {pid}: {e}")
                        
                except Exception as e:
                    logger.error(f"Failed to kill process {pid}: {e}")
            click.echo(f"Killed all processes on GPU {gpu}")
            return

        # Get all sweep IDs
        sweep_ids = get_sweep_ids()
        if not sweep_ids:
            raise click.ClickException("No sweep IDs found in the log file")

        # Confirm unless --force is used
        if not force:
            click.echo("The following sweeps agents will be killed:")
            for sweep_id in sweep_ids:
                click.echo(f"  - {sweep_id}")
            if gpu is not None:
                click.echo(f"Only agents on GPU {gpu} will be killed")
            if not click.confirm(f"\nThis will kill all agents for {len(sweep_ids)} sweeps. Continue?"):
                return
    except Exception as e:
        logger.error(f"Failed to kill sweeps: {e}")
        raise click.ClickException(str(e))
    
if __name__ == '__main__':
    cli() 