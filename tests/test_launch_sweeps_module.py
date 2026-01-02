import yaml
from pathlib import Path
from unittest.mock import patch
import itertools

import pytest

from easysweeps.launch_sweeps import create_sweeps
from easysweeps.constants import SWEEP_CONFIGS_DIR


@pytest.fixture
def sweep_files(temp_dir):
    sweep_dir = Path(temp_dir) / "sweeps"
    sweep_dir.mkdir(parents=True)

    # Simple template that will be formatted with lr and bs
    template = {
        "name": "exp_{learning_rate}_{batch_size}",
        "method": "grid",
        "parameters": {
            "learning_rate": {"value": 0.1},
            "batch_size": {"value": 64},
        },
    }

    variants = {
        "learning_rate": [0.01, 0.02],
        "batch_size": [32],
    }

    template_file = sweep_dir / "sweep_template.yaml"
    variants_file = sweep_dir / "sweep_variants.yaml"

    with template_file.open("w") as f:
        yaml.dump(template, f)
    with variants_file.open("w") as f:
        yaml.dump(variants, f)

    return sweep_dir, template_file, variants_file, variants


def make_side_effect(ids):
    def _side(*args, **kwargs):
        return f"https://wandb.ai/entity/project/sweeps/{ids.pop(0)}"
    return _side


def test_create_sweeps_success(sweep_files):
    sweep_dir, template_file, variants_file, variants = sweep_files
    combos = list(itertools.product(*variants.values()))
    expected_count = len(combos)
    ids = [f"id_{i}" for i in range(expected_count)]

    with patch("subprocess.check_output", side_effect=make_side_effect(ids)):
        created = create_sweeps(
            sweep_dir=sweep_dir,
            template_file=template_file,
            variants_file=variants_file,
        )

    assert len(created) == expected_count

    # Verify files were written and names match
    for (name, sweep_id), combo in zip(created, combos):
        lr, bs = combo
        assert name == f"exp_{lr}_{bs}"
        assert (sweep_dir / SWEEP_CONFIGS_DIR / f"sweep_{name}.yaml").exists()


def test_create_sweeps_invalid_template(sweep_files):
    sweep_dir, template_file, variants_file, _ = sweep_files
    # Overwrite template with invalid YAML
    template_file.write_text("::invalid yaml::")

    with pytest.raises(Exception):
        create_sweeps(
            sweep_dir=sweep_dir,
            template_file=template_file,
            variants_file=variants_file,
        ) 