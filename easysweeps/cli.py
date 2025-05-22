import click
from pathlib import Path
import logging

from easysweeps import launch_agents, launch_sweeps
from .config import config
from .utils import setup_logging
import subprocess

logger = logging.getLogger(__name__)

@click.group()
def cli():
    """EasySweeps - A powerful CLI tool for automating Weights & Biases sweep creation and management.

    This tool helps you create and manage multiple wandb sweeps efficiently by:
    - Creating multiple sweeps from a template and search space configuration
    - Launching sweep agents using systemd scope units for better process management
    - Managing GPU resources across multiple sweeps
    - Providing comprehensive logging and monitoring

    For detailed help on each command, use: easysweeps COMMAND --help
    """
    # Set up logging
    log_dir = Path(config.get("agent_log_dir"))
    setup_logging(log_dir)

@cli.command()
@click.option('--sweep-dir', type=click.Path(), help='Directory containing sweep configurations (default: from ez_config.yaml)')
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
        
        # Create and update created_sweeps.txt
        sweep_log = sweep_dir / "created_sweeps.txt"
        sweep_log.parent.mkdir(parents=True, exist_ok=True)
        
        with sweep_log.open('a') as f:
            for name, sweep_id in created_sweeps:
                f.write(f"{name} {sweep_id}\n")
        
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

    The command uses the following configuration from ez_config.yaml:
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
            sweep_ids = get_sweep_ids()
            if not sweep_ids:
                raise click.ClickException("No sweeps found. Have you created any sweeps?")

            click.echo("\nAvailable sweeps:")
            click.echo("-" * 50)
            sweep_log = Path(config.get("sweep_dir")) / "created_sweeps.txt"
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
    """Get list of sweep IDs from the log file.
    
    Returns:
        list: List of sweep IDs from created_sweeps.txt. Returns empty list if file doesn't exist.
    """
    try:
        sweep_log = Path(config.get("sweep_dir")) / "created_sweeps.txt"
        
        # Create the file if it doesn't exist
        if not sweep_log.exists():
            sweep_log.parent.mkdir(parents=True, exist_ok=True)
            sweep_log.touch()
            logger.info(f"Created new sweep log file at {sweep_log}")
            return []
        
        with sweep_log.open() as f:
            sweep_ids = []
            for line in f:
                if line.strip():
                    try:
                        name, sweep_id = line.strip().split()
                        sweep_ids.append(sweep_id)
                    except ValueError:
                        logger.warning(f"Invalid line format in {sweep_log}: {line.strip()}")
                        continue
        
        return sweep_ids
    except Exception as e:
        logger.error(f"Failed to get sweep IDs: {e}")
        return []


@cli.command()
def status():
    """Show status of all sweeps and running agents in a pretty format.
    
    This command displays:
    - Currently running agents in systemd scope units
    - GPU assignments for each agent
    - Status of each agent (running/stopped)
    - Sweeps that exist but have no running agents
    """
    try:
        # Get running scope units
        result = subprocess.run(['systemctl', '--user', 'list-units', '--type=scope'], 
                              capture_output=True, text=True)
        running_units = result.stdout.split('\n')

        # Parse all running units to get sweep IDs and their agents
        active_sweeps = {}  # sweep_id -> {name: str, agents: list of (gpu, agent, status)}
        
        for unit in running_units:
            if "wandb-agent-" in unit:
                parts = unit.split()
                if len(parts) > 0:
                    unit_name = parts[0]
                    try:
                        # Extract sweep_id, GPU and agent numbers from unit name
                        # Format: wandb-agent-{sweep_id}-{gpu}-{agent}.scope
                        parts = unit_name.split('-')
                        sweep_id = parts[2]
                        gpu = parts[3]
                        agent = parts[4].replace('.scope', '')
                        status = "running" if "active" in unit else "stopped"
                        
                        if sweep_id not in active_sweeps:
                            active_sweeps[sweep_id] = {
                                'name': sweep_id,  # Default to ID if name not found
                                'agents': []
                            }
                        active_sweeps[sweep_id]['agents'].append((gpu, agent, status))
                    except (IndexError, ValueError):
                        continue

        # Get sweep names from created_sweeps.txt for inactive sweeps
        sweep_log = Path(config.get("sweep_dir")) / "created_sweeps.txt"
        if sweep_log.exists():
            with sweep_log.open() as f:
                for line in f:
                    if line.strip():
                        name, sweep_id = line.strip().split()
                        if sweep_id not in active_sweeps:
                            active_sweeps[sweep_id] = {
                                'name': name,
                                'agents': []
                            }
                        else:
                            active_sweeps[sweep_id]['name'] = name

        # Create a pretty table
        click.echo("=== Sweeps and Agents Status ===\n")
        
        # First show sweeps with running agents
        active_sweeps_with_agents = {sid: info for sid, info in active_sweeps.items() if info['agents']}
        if active_sweeps_with_agents:
            click.echo("Active Sweeps:")
            click.echo("-" * 50)
            for sweep_id, info in active_sweeps_with_agents.items():
                click.echo(f"Sweep: {info['name']} (ID: {sweep_id})")
                click.echo("Agents:")
                for gpu, agent, status in sorted(info['agents'], key=lambda x: (int(x[0]), int(x[1]))):
                    status_color = "green" if status == "running" else "red"
                    click.echo(f"  GPU {gpu}, Agent {agent}: {click.style(status, fg=status_color)}")
                click.echo("-" * 50)

        # Then show sweeps without agents
        inactive_sweeps = {sid: info for sid, info in active_sweeps.items() if not info['agents']}
        if inactive_sweeps:
            click.echo("Inactive Sweeps (no running agents):\n")
            for sweep_id, info in inactive_sweeps.items():
                click.echo(f"{info['name']} (ID: {sweep_id})")

        if not active_sweeps:
            click.echo("No active sweeps found")
            
    except Exception as e:
        logger.error(f"Failed to show status: {e}")
        raise click.ClickException(str(e))
    
@cli.command()
@click.option('--force', is_flag=True, help='Force kill all sweeps and agents (requires confirmation)')
@click.option('--gpu', type=int, help='GPU number to kill agents from (optional)')
@click.option('--sweep', type=str, help='Sweep ID to kill agents for (optional)')
def kill(force, gpu, sweep):
    """Kill wandb sweep agents with flexible options.

    This command kills wandb sweep agents that are running in systemd scope units.
    You can specify:
    - --force to kill all sweeps and agents (requires confirmation)
    - --gpu to kill all agents on a specific GPU
    - --sweep to kill all agents for a specific sweep
    - --sweep and --gpu together to kill agents for a specific sweep on a specific GPU
    - No options to see list of active sweeps

    Examples:
        easysweeps kill --force  # Kills all sweeps and agents (with confirmation)
        easysweeps kill --gpu 0  # Kills all agents on GPU 0
        easysweeps kill --sweep abc123  # Kills all agents for sweep abc123
        easysweeps kill --sweep abc123 --gpu 0  # Kills agents for sweep abc123 on GPU 0
        easysweeps kill  # Shows list of active sweeps
    """
    try:
        # Handle force kill all
        if force:
            if not click.confirm("This will kill ALL sweeps and agents. Continue?"):
                return
            # Kill all wandb agent scope units
            subprocess.run(['systemctl', '--user', '--no-pager', 'stop', 'wandb-agent-*.scope'])
            click.echo("Killed all wandb agent units")
            return

        # Get running scope units
        result = subprocess.run(['systemctl', '--user', 'list-units', '--type=scope'], 
                              capture_output=True, text=True)
        running_units = result.stdout.split('\n')

        # Parse all running units to get sweep IDs
        active_sweeps = set()
        for unit in running_units:
            if "wandb-agent-" in unit:
                parts = unit.split()
                if len(parts) > 0:
                    unit_name = parts[0]
                    try:
                        # Extract sweep_id from unit name
                        # Format: wandb-agent-{sweep_id}-{gpu}-{agent}.scope
                        sweep_id = unit_name.split('-')[2]
                        active_sweeps.add(sweep_id)
                    except (IndexError, ValueError):
                        continue

        # If no sweep or gpu provided, show all available sweeps
        if not sweep and gpu is None:
            if not active_sweeps:
                click.echo("No active sweeps found")
                return

            click.echo("Active sweeps:")
            click.echo("-" * 50)
            for sweep_id in sorted(active_sweeps):
                click.echo(f"Sweep ID: {sweep_id}")
                click.echo("-" * 50)
            return

        # Construct the unit pattern based on provided options
        if sweep:
            unit_pattern = f"wandb-agent-{sweep}"
            if gpu is not None:
                unit_pattern += f"-{gpu}"
            else:
                unit_pattern += "-*"
            unit_pattern += "-*"  # For agent number
        else:
            # Only gpu specified
            unit_pattern = f"wandb-agent-*-{gpu}-*.scope"
            sweep = "all sweeps"  # For message

        unit_pattern += ".scope"

        # Stop the matching systemd units
        subprocess.run(['systemctl', '--user', '--no-pager', 'stop', unit_pattern])
        
        # Construct appropriate message
        if gpu is not None:
            click.echo(f"Killed agents for {sweep} on GPU {gpu}")
        else:
            click.echo(f"Killed all agents for sweep {sweep}")
            
    except Exception as e:
        logger.error(f"Failed to kill agents: {e}")
        raise click.ClickException(str(e))
    
if __name__ == '__main__':
    cli() 