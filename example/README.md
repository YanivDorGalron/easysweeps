# Example: Running W&B Sweeps with EasySweeps

This example demonstrates how to use EasySweeps to run Weights & Biases (W&B) hyperparameter sweeps with a simple PyTorch training script.

## Overview

The `train.py` script is a minimal example that:
- Trains a simple neural network (784 → 128 → 10) using PyTorch
- Uses W&B for experiment tracking and hyperparameter management
- Generates synthetic data for demonstration purposes
- Logs training loss and epoch metrics to W&B

The script reads hyperparameters from `wandb.config`, which is automatically populated by W&B sweeps.

## Quick Start

### 1. Initialize the Project

First, initialize the EasySweeps project structure:

```bash
cd example
ez init
```

This command creates:
- `ez_config.yaml` - Configuration file for your project
- `sweeps/` directory - Contains sweep configuration files
- `sweeps/sweep_template.yaml` - Template defining the sweep structure
- `sweeps/sweep_variants.yaml` - Variants that create multiple sweeps

### 2. Configure Your Project (Optional)

Edit `ez_config.yaml` to set your W&B entity and project name:

```yaml
sweep_dir: "sweeps"
agent_log_dir: "agent_logs"
entity: null                 # Your W&B username or team name (null = default)
project: "example"           # Your W&B project name
```

### 3. Customize Sweep Configuration (Optional)

The default template sweeps over `learning_rate` and `batch_size`. You can modify:
- `sweeps/sweep_template.yaml` - Change hyperparameters, method (grid/bayes/random), or metric
- `sweeps/sweep_variants.yaml` - Add more variant combinations

**Note:** The example `train.py` only uses `learning_rate` from the config. The `batch_size` parameter in the template won't affect training unless you modify `train.py` to use it.

### 4. Create Sweeps

Generate W&B sweeps from your template and variants:

```bash
ez sweep
```

This creates one or more sweeps in W&B (one per variant combination). The command will output sweep IDs that you'll need for the next step.

### 5. Launch Agents

Start sweep agents on your GPUs:

```bash
# List available sweeps
ez agent

# Launch agents on specific GPUs
ez agent <SWEEP_ID> --gpu-list 0 1 2

# Launch multiple agents per GPU
ez agent <SWEEP_ID> --gpu-list 0 --agents-per-sweep 3
```

Replace `<SWEEP_ID>` with the ID from step 4. Agents will automatically run training jobs and log results to W&B.

### 6. Monitor Status

Check the status of your sweeps and running agents:

```bash
ez status
```

This shows:
- All sweeps in your project
- Running agents and their GPU assignments
- Runtime information

### 7. Stop Agents (if needed)

Stop agents when you're done or need to free up resources:

```bash
# List active sweeps
ez kill

# Kill all agents
ez kill --force

# Kill agents on a specific GPU
ez kill --gpu 0

# Kill agents for a specific sweep
ez kill --sweep <SWEEP_ID>

# Kill agents for a specific sweep on a specific GPU
ez kill --sweep <SWEEP_ID> --gpu 0
```

## Understanding train.py

The `train.py` script demonstrates the minimal setup needed for W&B sweeps:

```python
# Initialize W&B - this reads hyperparameters from the sweep
wandb.init()
config = wandb.config

# Use config values in your training
optimizer = optim.Adam(model.parameters(), lr=config.learning_rate)

# Log metrics during training
wandb.log({"loss": loss.item(), "epoch": epoch})
```

Key points:
- `wandb.init()` automatically connects to the sweep when run by an agent
- `wandb.config` contains hyperparameters defined in your sweep template
- `wandb.log()` sends metrics to W&B for visualization
- The script uses synthetic data for simplicity - replace with your own dataset

## Complete Workflow Example

```bash
# 1. Initialize
cd example
ez init

# 2. (Optional) Edit ez_config.yaml with your W&B project details

# 3. Create sweeps
ez sweep
# Output: Created sweep myproject/example_sweep_mnist:abc123 [1/2]
#          Created sweep myproject/example_sweep_cifar10:def456 [2/2]

# 4. Launch agents on GPUs 0, 1, and 2
ez agent abc123 --gpu-list 0 1 2
ez agent def456 --gpu-list 0 1 2

# 5. Monitor progress
ez status

# 6. View results in W&B dashboard
# Visit https://wandb.ai to see your experiments

# 7. Stop agents when done
ez kill --force
```

## Troubleshooting

- **"Template file not found"**: Make sure you've run `ez init` first
- **"No sweeps found"**: Run `ez sweep` to create sweeps before launching agents
- **Agents not starting**: Check that you're logged into W&B (`wandb login`)
- **GPU not available**: Verify GPU availability with `nvidia-smi`

## Next Steps

- Modify `train.py` to use your own dataset and model
- Customize `sweeps/sweep_template.yaml` with your hyperparameter search space
- Add more variants in `sweeps/sweep_variants.yaml` for multi-dataset experiments
- Explore W&B dashboard for hyperparameter analysis and visualization

