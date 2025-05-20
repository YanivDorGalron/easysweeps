import click
from pathlib import Path
import libtmux
from . import launch_agents
from . import launch_sweeps
import yaml
import logging
from .config import config
from .utils import setup_logging
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
@click.option('--gpu-list', help='Comma-separated list of GPU indices to use (e.g., "0,1,2")')
@click.option('--all-gpus', is_flag=True, help='Launch all sweeps on all GPUs instead of distributing one per GPU')
def agent(gpu_list, all_gpus):
    """Launch wandb sweep agents in tmux sessions.

    This command launches wandb sweep agents in tmux sessions, distributing them
    across the specified GPUs. Each agent runs in its own tmux window for better
    process management and monitoring.

    Example:
        easysweeps agent --conda-env my_env --gpu-list 0,1 --entity my_team --project my_project
    """
    try:
        # Parse GPU list
        if gpu_list:
            try:
                gpu_list = [int(gpu.strip()) for gpu in gpu_list.split(',')]
            except ValueError:
                raise click.ClickException("GPU list must be comma-separated integers (e.g., '0,1,2')")
        else:
            gpu_list = None

        # Use provided values or defaults from config
        args = type('Args', (), {
            'conda_env': config.get("conda_env"),
            'sweep_log_dir': config.get("sweep_dir"),
            'gpu_list': gpu_list,
            'entity': config.get("entity"),
            'project': config.get("project"),
            'all_gpus': all_gpus
        })

        if not args.gpu_list:
            raise click.ClickException("No GPUs specified. Use --gpu-list to specify GPUs (e.g., --gpu-list 0,1,2).")

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

@cli.command()
@click.argument('sweep_id', required=False)
@click.option('--gpu', type=int, required=True, help='GPU number to kill the agent from')
def kill(sweep_id, gpu):
    """Kill a specific wandb sweep agent running on a specific GPU.

    This command kills a wandb sweep agent that is running in a tmux session
    on the specified GPU. The sweep_id should match the session name, and the
    GPU number should match the window name (e.g., "gpu0").v
    If this is the last agent for the sweep, the entire session will be killed.

    Example:
        easysweeps kill abc123 --gpu 0  # Kills the agent for sweep abc123 running on GPU 0
    """
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

        window_name = f"gpu{gpu}"
        window = session.find_where({"window_name": window_name})
        
        if window:
            window.kill_window()
            click.echo(f"Killed agent for sweep {sweep_id} on GPU {gpu}")
            
            # Check if this was the last window in the session
            remaining_windows = session.windows
            if len(remaining_windows) == 1: # default window
                session.kill_session()
                click.echo(f"Killed session for sweep {sweep_id} (no more agents running)")
        else:
            raise click.ClickException(f"No agent found for sweep {sweep_id} on GPU {gpu}")
            
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
        click.echo("\n=== Sweeps and Agents Status ===\n")
        
        for name, sweep_id in sweeps:
            click.echo(f"Sweep: {name}")
            click.echo(f"ID: {sweep_id}")
            
            # Find running agents for this sweep
            running_agents = []
            for session in sessions:
                if session.name.startswith(sweep_id):
                    # Get all windows in this session
                    windows = session.windows
                    for window in windows:
                        if window.name.startswith('gpu'):
                            gpu = window.name.replace('gpu', '')
                            # Check if the window has a running process
                            pane = window.attached_pane
                            if pane and pane.pane_pid:
                                running_agents.append((gpu, "running"))
                            else:
                                running_agents.append((gpu, "stopped"))
            
            if running_agents:
                click.echo("Agents:")
                for gpu, status in sorted(running_agents, key=lambda x: int(x[0])):
                    status_color = "green" if status == "running" else "red"
                    click.echo(f"  GPU {gpu}: {click.style(status, fg=status_color)}")
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
def kill_all(force):
    """Kill all sweep agents and their tmux sessions.
    
    This command will:
    - Find all sweep sessions from your sweep log
    - Kill all associated tmux sessions
    - Clean up all agent windows
    
    Use the --force flag to skip confirmation.
    """
    try:
        # Get all sweep IDs
        sweep_ids = get_sweep_ids()
        if not sweep_ids:
            raise click.ClickException("No sweep IDs found in the log file")

        # Confirm unless --force is used
        if not force:
            click.echo("The following sweep sessions will be killed:")
            for sweep_id in sweep_ids:
                click.echo(f"  - {sweep_id}")
            if not click.confirm(f"\nThis will kill all {len(sweep_ids)} sweep sessions. Continue?"):
                return

        # Kill all sessions
        server = libtmux.Server()
        killed_count = 0
        
        for sweep_id in sweep_ids:
            # Find all sessions that start with this sweep_id
            sessions = server.find_where({"session_name": sweep_id})
            if sessions:
                try:
                    sessions.kill_session()
                    killed_count += 1
                    click.echo(f"Killed session for sweep {sweep_id}")
                except Exception as e:
                    logger.error(f"Failed to kill session for sweep {sweep_id}: {e}")
                    continue

        if killed_count > 0:
            click.echo(f"\nSuccessfully killed {killed_count} sweep sessions")
        else:
            click.echo("\nNo running sweep sessions found")
            
    except Exception as e:
        logger.error(f"Failed to kill all sweeps: {e}")
        raise click.ClickException(str(e))
    
if __name__ == '__main__':
    cli() 