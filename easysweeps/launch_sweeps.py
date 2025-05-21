# create_sweeps.py
import itertools
import subprocess
from copy import deepcopy
from pathlib import Path
import yaml
import logging
from .config import config

logger = logging.getLogger(__name__)

def create_sweeps(sweep_dir=None, template_file=None, variants_file=None):
    """Create wandb sweeps based on template and variants configuration"""
    # Use provided paths or defaults from config
    sweep_dir = Path(sweep_dir or config.get("sweep_dir"))
    log_file = sweep_dir / "created_sweeps.txt"
    sweep_dir.mkdir(parents=True, exist_ok=True)

    # Load template and variants
    try:
        with open(template_file) as f:
            sweep_template = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load sweep template: {e}")
        raise

    try:
        with open(variants_file) as f:
            variants = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load variants file: {e}")
        raise

    # Cartesian product
    keys, values = zip(*variants.items())
    combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
    total = len(combinations)

    created_sweeps = []
    for i, combo in enumerate(combinations):
        try:
            sweep_config = deepcopy(sweep_template)
            for k, v in combo.items():
                sweep_config["parameters"][k]["value"] = v

            sweep_config["name"] = sweep_name = sweep_config["name"].format(**combo)

            # Save to YAML
            sweep_file = sweep_dir / f"sweep_{sweep_name}.yaml"
            with open(sweep_file, "w") as f:
                yaml.dump(sweep_config, f)

            # Create sweep without launching agent
            logger.info(f"Creating sweep: {sweep_name} [{i + 1}/{total}]")
            out = subprocess.check_output(
                ["wandb", "sweep", str(sweep_file)],
                text=True,
                stderr=subprocess.STDOUT
            )
            sweep_id = out.strip().split("/")[-1]
            created_sweeps.append((sweep_name, sweep_id))
            logger.info(f"Created sweep {sweep_name} with ID {sweep_id}")

        except Exception as e:
            import traceback
            logger.error(f"Failed to create sweep {i + 1}: {e}\n{traceback.format_exc()}")
            continue

    # Write to log file
    with open(log_file, "w") as f:
        for name, sweep_id in created_sweeps:
            f.write(f"{name} {sweep_id}\n")

    logger.info(f"Created {len(created_sweeps)} sweeps successfully")
    return created_sweeps

