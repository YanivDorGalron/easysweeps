# create_sweeps.py
import itertools
import subprocess
from copy import deepcopy
from pathlib import Path

import yaml

sweep_dir = Path("GINPool/sweeps")
log_file = sweep_dir / "created_sweeps.txt"
log_file.parent.mkdir(parents=True, exist_ok=True)

# Load template
with (sweep_dir / "sweep_template_histograph.yaml").open() as f:
    sweep_template = yaml.safe_load(f)

# Search space
search_space = {
    "num_layers": [16, 32, 64],
    "dataset": ["IMDBBINARY", "IMDBMULTI", "PROTEINS", "PTC"],
}

# Cartesian product
keys, values = zip(*search_space.items())
combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
total = len(combinations)

created_sweeps = []
for i, combo in enumerate(combinations):
    sweep_config = deepcopy(sweep_template)
    for k, v in combo.items():
        sweep_config["parameters"][k]["value"] = v

    if "checkpoint_path" in sweep_config:
        suffix = "_pool" if combo.get("train_only_pooling", "false") == "true" else "_full"
    else:
        suffix = ""
    sweep_config["name"] = sweep_name = sweep_config["name"].format(**combo) + suffix

    # Save to YAML
    sweep_file = sweep_dir / f"sweep_{sweep_name}.yaml"
    with open(sweep_file, "w") as f:
        yaml.dump(sweep_config, f)

    # Create sweep without launching agent
    print(f"Creating sweep: {sweep_name} [{i + 1}/{total}]")
    out = subprocess.check_output(
        ["wandb", "sweep", str(sweep_file)],
        text=True,
        stderr=subprocess.STDOUT
    )
    print(out)
    sweep_id = out.strip().split("/")[-1]
    created_sweeps.append((sweep_name, sweep_id))

# Write to log file
with open(log_file, "w") as f:
    for name, sweep_id in created_sweeps:
        f.write(f"{name} {sweep_id}\n")
