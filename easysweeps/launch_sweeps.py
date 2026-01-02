# create_sweeps.py
import itertools
import subprocess
from copy import deepcopy
from pathlib import Path
import click
import yaml
import logging
import wandb
from .config import config
from .constants import SWEEP_CONFIGS_DIR

logger = logging.getLogger(__name__)

def _load_and_validate_template(template_file):
    """Load and validate the sweep template file."""
    try:
        with open(template_file) as f:
            template = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load sweep template: {e}")
        raise

    if not isinstance(template, dict):
        raise ValueError(
            f"Sweep template must be a YAML mapping (dictionary). Got type: {type(template)}"
        )

    if "parameters" not in template or not isinstance(template.get("parameters"), dict):
        raise ValueError("Sweep template is missing required 'parameters' mapping.")
    
    return template

def _load_and_validate_variants(variants_file):
    """Load and validate the variants file."""
    try:
        with open(variants_file) as f:
            variants = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load variants file: {e}")
        raise

    if not isinstance(variants, dict):
        raise ValueError("Variants file must be a YAML mapping from parameter names to lists of values.")
    
    return variants

def _generate_sweep_config(template, combo):
    """Generate a single sweep configuration from template and combination.
    
    Args:
        template (dict): The sweep template.
        combo (dict): A dictionary mapping parameter names to their values for this combination.
    
    Returns:
        dict: A single sweep configuration.
    """
    sweep_config = deepcopy(template)
    for k, v in combo.items():
        # Ensure parameter dict exists
        if k not in sweep_config["parameters"]:
            sweep_config["parameters"][k] = {}
        sweep_config["parameters"][k]["value"] = v

    # Format name if present
    if "name" in sweep_config:
        sweep_config["name"] = sweep_config["name"].format(**combo)
        
    return sweep_config

def _register_sweep(sweep_file, project, entity):
    """Register the sweep with W&B using the CLI."""
    cmd = ["wandb", "sweep", "--entity", entity]
    if project:
        cmd.extend(["--project", project])
    cmd.append(str(sweep_file))

    out = subprocess.check_output(
        cmd,
        text=True,
        stderr=subprocess.STDOUT
    )
    return out.strip().split("/")[-1]

def create_sweeps(sweep_dir=None, template_file=None, variants_file=None):
    """Create wandb sweeps based on template and variants configuration"""
    # Use provided paths or defaults from config
    sweep_dir = Path(sweep_dir or config.get("sweep_dir"))
    sweep_dir.mkdir(parents=True, exist_ok=True)

    # Create configs directory
    configs_dir = sweep_dir / SWEEP_CONFIGS_DIR
    configs_dir.mkdir(parents=True, exist_ok=True)

    # Load and validate configurations
    sweep_template = _load_and_validate_template(template_file)
    variants = _load_and_validate_variants(variants_file)

    # Cartesian product
    keys, values = zip(*variants.items())
    combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
    total = len(combinations)

    # Get W&B context
    entity = config.get("entity") or wandb.api.default_entity
    project = config.get("project")
    project_str = f"{project}/" if project else ""

    created_sweeps = []
    for i, combo in enumerate(combinations):
        try:
            sweep_config = _generate_sweep_config(sweep_template, combo)
            sweep_name = sweep_config.get("name", f"sweep_{i}")

            # Save to YAML
            sweep_file = configs_dir / f"sweep_{sweep_name}.yaml"
            with open(sweep_file, "w") as f:
                yaml.dump(sweep_config, f)

            # Register sweep
            sweep_id = _register_sweep(sweep_file, project, entity)
            
            created_sweeps.append((sweep_name, sweep_id))
            click.echo(f"Created sweep {project_str}{sweep_name}:{sweep_id} [{i + 1}/{total}]")

        except Exception as e:
            import traceback
            logger.error(f"Failed to create sweep {i + 1}: {e}\n{traceback.format_exc()}")
            continue

    logger.debug(f"Created {len(created_sweeps)} sweeps successfully")
    return created_sweeps
