import click
from pathlib import Path
import logging
import subprocess
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import wandb
import shutil
import yaml
from datetime import datetime


from easysweeps import launch_agents, launch_sweeps
from .config import config
from .utils import setup_logging

logger = logging.getLogger(__name__)

@click.group()
def cli():
    """EasySweeps - A CLI tool for automating Weights & Biases sweep management.

    This tool helps you create and manage W&B sweeps efficiently by:

    \b
    - Creating sweeps from a template and variants configuration
    - Launching agents with systemd scope units for process management
    - Managing GPU resources across multiple sweeps
    - Monitoring sweep status and agent activity

    For detailed help on each command, use: ez COMMAND --help
    """
    # Set up logging
    log_dir = Path(config.get("agent_log_dir"))
    setup_logging(log_dir)

@cli.command()
def init():
    """Initialize a new EasySweeps project.
    
    This command scaffolds the project by creating:
    - ez_config.yaml (if not exists)
    - sweeps/ directory (if not exists)
    - sweeps/sweep_template.yaml (if not exists)
    - sweeps/sweep_variants.yaml (if not exists)
    """
    # 1. Create ez_config.yaml
    config_path = Path("ez_config.yaml")
    if not config_path.exists():
        # Overwrite with commented version for better UX
        with open(config_path, "w") as f:
            f.write(f'''sweep_dir: "sweeps"          # Directory for sweep configurations
agent_log_dir: "agent_logs"  # Directory for agent logs
entity: null                 # W&B entity name (username or team name). Set to null to use default.
project: "{Path.cwd().name}"                # W&B project name
''')
        click.echo(f"Created {config_path}")
    else:
        click.echo(f"{config_path} already exists, skipping.")

    # 2. Create sweeps directory
    sweeps_dir = Path("sweeps")
    if not sweeps_dir.exists():
        sweeps_dir.mkdir()
        click.echo(f"Created directory {sweeps_dir}")
    else:
        click.echo(f"Directory {sweeps_dir} already exists, skipping.")

    # 3. Create sweep_template.yaml
    template_path = sweeps_dir / "sweep_template.yaml"
    if not template_path.exists():
        with open(template_path, "w") as f:
            f.write("""name: "example_sweep_{dataset}"
method: "grid"
metric:
  name: "loss"
  goal: "minimize"
parameters:
  learning_rate:
    values: [0.001, 0.01]
  batch_size:
    values: [32, 64]
  dataset:
    value: None  # This will be replaced by variants
program: "train.py"
""")
        click.echo(f"Created {template_path}")
    else:
        click.echo(f"{template_path} already exists, skipping.")

    # 4. Create sweep_variants.yaml
    variants_path = sweeps_dir / "sweep_variants.yaml"
    if not variants_path.exists():
        with open(variants_path, "w") as f:
            f.write("""dataset: ['mnist', 'cifar10']
""")
        click.echo(f"Created {variants_path}")
    else:
        click.echo(f"{variants_path} already exists, skipping.")

    click.echo("Initialization complete!")

@cli.command()
@click.option('--sweep-dir', type=click.Path(), help='Directory containing sweep configurations (default: from ez_config.yaml)')
@click.option('--template', type=click.Path(), help='Sweep template file (default: sweep_dir/sweep_template.yaml)')
@click.option('--variants', type=click.Path(), help='Sweep variants configuration file (default: sweep_dir/sweep_variants.yaml)')
def sweep(sweep_dir, template, variants):
    """Create W&B sweeps from a template and variants configuration.

    This command creates multiple W&B sweeps by combining a template configuration
    with a variants definition. The template defines base sweep parameters while
    the variants file specifies different parameter values to create separate sweeps.

    \b
    Examples:
        ez sweep                           # Use defaults from ez_config.yaml
        ez sweep --sweep-dir my_sweeps/    # Use custom sweep directory
    """
    try:
        # Use provided paths or defaults from config
        sweep_dir = Path(sweep_dir or config.get("sweep_dir"))
        template = Path(template) if template else (sweep_dir / "sweep_template.yaml")
        variants = Path(variants) if variants else (sweep_dir / "sweep_variants.yaml")

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

@cli.command(context_settings=dict(allow_extra_args=True))
@click.argument('sweep_id', required=False)
@click.option('--gpu-list', '-g', multiple=True, type=int, help='GPU indices to use (e.g., --gpu-list 0 1 2). Required when launching agents.')
@click.option('--agents-per-sweep', type=int, default=1, help='Number of agents to launch per sweep on each GPU')
@click.pass_context
def agent(ctx, sweep_id, gpu_list, agents_per_sweep):
    """Launch W&B sweep agents on specified GPUs.

    Launches sweep agents as systemd scope units, distributing them across GPUs.
    Each agent runs in its own scope unit for better process management.

    \b
    Examples:
        ez agent                                # List available sweeps
        ez agent abc123 --gpu-list 0 1 2        # Launch on GPUs 0, 1, 2
        ez agent abc123 -g 0                    # Single GPU
        ez agent abc123 -g 0 --agents-per-sweep 3  # 3 agents on GPU 0
    """
    try:
        # We use ctx.args because Click options (like --gpu-list) take a fixed number of values.
        # This allows us to capture space-separated indices like `--gpu-list 0 1 2` where '1' and '2'
        # are treated as extra arguments by Click's parser.
        gpu_list = sorted(set(gpu_list) | {int(arg) for arg in ctx.args if arg.isdigit()})

        # If no sweep_id provided, show all available sweeps (no GPU list needed)
        if not sweep_id:
            entity = config.get("entity")
            project = config.get("project")
            try:
                api = wandb.Api()
            except Exception as e:
                raise click.ClickException(f"Failed to initialize W&B API: {e}")
            
            try:
                sweeps = api.project(project, entity=entity).sweeps()
                if not sweeps:
                    raise click.ClickException("No sweeps found. Create sweeps first with 'ez sweep'.")

                click.echo("\nAvailable sweeps:")
                click.echo("-" * 50)
                for sweep in sweeps:
                    click.echo(f"  {sweep.name} (ID: {sweep.id})")
                click.echo("-" * 50)
                click.echo("\nTo launch agents: ez agent <SWEEP_ID> --gpu-list 0 1 2")
                return
            except Exception as e:
                raise click.ClickException(f"Failed to fetch sweeps from W&B API: {e}")

        # GPU list is required when launching agents
        if not gpu_list:
            raise click.ClickException("--gpu-list is required when launching agents. Use 'ez agent' to list sweeps.")

        # Use provided values or defaults from config
        args = type('Args', (), {
            'sweep_log_dir': config.get("sweep_dir"),
            'gpu_list': gpu_list,
            'project': config.get("project"),
            'all_gpus': True,  # Always use all specified GPUs
            'agents_per_sweep': agents_per_sweep,
            'sweep_id': sweep_id
        })

        # Run the agent launch
        launch_agents.launch_agents(args)
        click.echo("Successfully launched sweep agents")
        
    except Exception as e:
        logger.error(f"Failed to launch agents: {e}")
        raise click.ClickException(str(e))

@cli.command()
@click.option('--show-runs', is_flag=True, help='Show the number of runs for each sweep (may be slow)')
def status(show_runs):
    """Show status of all sweeps and running agents.

    \b
    Displays:
      - Active sweeps with running agents and GPU assignments
      - Agent status (running/stopped) with runtime duration
      - Inactive sweeps with no running agents
    """
    try:
        # Get running scope units
        result = subprocess.run(['systemctl', '--user', 'list-units', '--type=scope'], 
                              capture_output=True, text=True)
        running_units = result.stdout.split('\n')

        # Parse all running units to get sweep IDs
        active_sweeps = {}
        for unit in running_units:
            if "wandb-agent-" in unit:
                parts = unit.split()
                if len(parts) > 0:
                    unit_name = parts[0]
                    try:
                        # Extract sweep_id, GPU and agent numbers from unit name
                        # Format: wandb-agent-{sweep_id}-{gpu}-{agent}.scope
                        unit_parts = unit_name.split('-')
                        if len(unit_parts) >= 5 and unit_parts[0] == "wandb" and unit_parts[1] == "agent" and unit_name.endswith('.scope'):
                            sweep_id = unit_parts[2]
                            gpu = unit_parts[3]
                            agent = unit_parts[4].replace('.scope', '')
                        # Validate that GPU and agent parts are numeric
                            if gpu.isdigit() and agent.isdigit():
                                status = "running" if "active" in unit else "stopped"
                                
                                runtime_str = ""
                                if status == "running":
                                    try:
                                        # Get runtime
                                        ts_result = subprocess.run(
                                            ['systemctl', '--user', 'show', '-p', 'ActiveEnterTimestamp', unit_name],
                                            capture_output=True, text=True
                                        )
                                        # ActiveEnterTimestamp=Sat 2025-12-27 20:20:18 IST
                                        val = ts_result.stdout.strip().split('=', 1)[1]
                                        if val and val != 'n/a':
                                            parts = val.split()
                                            if len(parts) >= 3:
                                                # Parse YYYY-MM-DD HH:MM:SS
                                                date_str = f"{parts[1]} {parts[2]}"
                                                start_time = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                                                duration = datetime.now() - start_time
                                                
                                                total_seconds = int(duration.total_seconds())
                                                hours, remainder = divmod(total_seconds, 3600)
                                                minutes, seconds = divmod(remainder, 60)
                                                
                                                if hours > 0:
                                                    r_str = f"{hours}h {minutes}m"
                                                elif minutes > 0:
                                                    r_str = f"{minutes}m {seconds}s"
                                                else:
                                                    r_str = f"{seconds}s"
                                                runtime_str = f" ({r_str})"
                                    except Exception:
                                        pass

                                if sweep_id not in active_sweeps:
                                    active_sweeps[sweep_id] = {
                                        'name': sweep_id,  # Default to ID if name not found
                                        'agents': []
                                    }
                                active_sweeps[sweep_id]['agents'].append((gpu, agent, status + runtime_str))
                    except (IndexError, ValueError):
                        continue

        # Get W&B API sweep information
        entity = config.get("entity")
        project = config.get("project")
        try:
            api = wandb.Api()
        except Exception as e:
            raise click.ClickException(f"Failed to initialize W&B API: {e}")

        click.echo("\n=== W&B Sweeps Status ===\n")
        
        try:
            sweeps = api.project(project, entity=entity).sweeps()
            if sweeps:
                # Update active_sweeps with sweep names and run counts from W&B API
                for sweep in sweeps:
                    run_count = len(sweep.runs) if show_runs else None
                    if sweep.id not in active_sweeps:
                        active_sweeps[sweep.id] = {
                            'name': sweep.name,
                            'agents': [],
                            'run_count': run_count
                        }
                    else:
                        active_sweeps[sweep.id]['name'] = sweep.name
                        if show_runs:
                            active_sweeps[sweep.id]['run_count'] = run_count

                # First show sweeps with running agents
                active_sweeps_with_agents = {sid: info for sid, info in active_sweeps.items() if info['agents']}
                if active_sweeps_with_agents:
                    click.echo("Active Sweeps:")
                    click.echo("-" * 50)
                    for sweep_id, info in active_sweeps_with_agents.items():
                        run_info = f" [Launched Runs: {info.get('run_count', 0)}]" if show_runs else ""
                        click.echo(f"Sweep: {info['name']} (ID: {sweep_id}){run_info}")
                        
                        # Group agents by GPU
                        gpu_map = {}
                        for gpu, agent, status in info['agents']:
                            if gpu not in gpu_map:
                                gpu_map[gpu] = []
                            gpu_map[gpu].append((agent, status))
                        
                        for gpu in sorted(gpu_map.keys(), key=int):
                            agents = gpu_map[gpu]
                            agent_strings = []
                            for agent, status in sorted(agents, key=lambda x: int(x[0])):
                                status_color = "green" if status.startswith("running") else "red"
                                agent_strings.append(f"A{agent} ({click.style(status, fg=status_color)})")
                            
                            click.echo(f"  GPU {gpu} | Agents: {', '.join(agent_strings)}")
                        click.echo("-" * 50)

                # Then show sweeps without agents
                inactive_sweeps = {sid: info for sid, info in active_sweeps.items() if not info['agents']}
                if inactive_sweeps:
                    click.echo("\nInactive Sweeps (no running agents):")
                    click.echo("-" * 50)
                    for sweep_id, info in inactive_sweeps.items():
                        run_info = f" [Launched Runs: {info.get('run_count', 0)}]" if show_runs else ""
                        click.echo(f"   {info['name']} (ID: {sweep_id}){run_info}")
            else:
                click.echo("\nNo W&B sweeps found in project. To create a sweep, use:")
                click.echo("  ez sweep --sweep-dir <your_sweep_dir>")
        except wandb.errors.CommError as e:
            click.echo("We did not find any sweeps in your project.")
            click.echo("Have you created a sweep yet? If you have, please check your configuration:")
            click.echo(f"  Entity: {entity}")
            click.echo(f"  Project: {project}")
            click.echo("Make sure these values are correct in your ez_config.yaml file.")
            click.echo("if you haven't created a sweep yet, please create a sweep first. using:")
            click.echo(f"  ez sweep")
        except Exception as e:
            click.echo(f"Unexpected error while fetching W&B sweeps: {str(e)}")
            click.echo("Please check your W&B configuration and try again.")
    except Exception as e:
        logger.error(f"Failed to show status: {e}")
        raise click.ClickException(str(e))
    
@cli.command()
@click.option('--force', is_flag=True, help='Kill all agents (requires confirmation)')
@click.option('--gpu', type=str, help='Kill agents on a specific GPU')
@click.option('--sweep', type=str, help='Kill agents for a specific sweep')
def kill(force, gpu, sweep):
    """Kill running sweep agents.

    Stop agents running in systemd scope units. With no options, shows active sweeps.

    \b
    Examples:
        ez kill                         # List active sweeps
        ez kill --force                 # Kill all agents (with confirmation)
        ez kill --gpu 0                 # Kill all agents on GPU 0
        ez kill --sweep abc123          # Kill all agents for sweep abc123
        ez kill --sweep abc123 --gpu 0  # Kill specific sweep on specific GPU
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
                        unit_parts = unit_name.split('-')
                        if len(unit_parts) >= 5 and unit_parts[0] == "wandb" and unit_parts[1] == "agent" and unit_name.endswith('.scope'):
                            sweep_id = unit_parts[2]
                            # Validate that GPU and agent parts are numeric
                            gpu_part = unit_parts[3]
                            agent_part = unit_parts[4].replace('.scope', '')
                            if gpu_part.isdigit() and agent_part.isdigit():
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
            # Only gpu specified - use a more precise pattern
            # First get all running units
            result = subprocess.run(['systemctl', '--user', 'list-units', '--type=scope'], 
                                  capture_output=True, text=True)
            running_units = result.stdout.split('\n')
            
            # Filter units that match the GPU
            matching_units = []
            for unit in running_units:
                if "wandb-agent-" in unit:
                    parts = unit.split()
                    if len(parts) > 0:
                        unit_name = parts[0]
                        try:
                            # Extract GPU from unit name
                            # Format: wandb-agent-{sweep_id}-{gpu}-{agent}.scope
                            unit_parts = unit_name.split('-')
                            if len(unit_parts) >= 5 and unit_parts[0] == "wandb" and unit_parts[1] == "agent" and unit_name.endswith('.scope'):
                                unit_gpu = unit_parts[3]
                                agent_part = unit_parts[4].replace('.scope', '')
                                if unit_gpu.isdigit() and agent_part.isdigit() and unit_gpu == str(gpu):
                                    matching_units.append(unit_name)
                        except (IndexError, ValueError):
                            continue
            
            # Stop each matching unit individually
            for unit in matching_units:
                subprocess.run(['systemctl', '--user', '--no-pager', 'stop', unit])
            
            click.echo(f"Killed all agents on GPU {gpu}")
            return

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