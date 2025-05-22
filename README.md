# EasySweeps

A command-line tool created for automating Weights & Biases sweeps across multiple GPUs. 

## Motivation

While Weights & Biases (W&B) provides a robust platform for experiment tracking and sweep management, working at scale often exposes several pain points. **EasySweeps** was built to address the following common challenges:

1. **Repetitive setup**  
   Launching the same sweep across different datasets or configurations often requires manual duplication and editing of sweep files.

2. **Limited agent control**  
   W&B does not provide built-in support for stopping a specific sweep agent or terminating all agents running on a particular GPU, making process management frustrating.

3. **Code consistency issues**  
   Agents always run the most recent version of the code. If the codebase changes during an ongoing sweep, new runs may behave inconsistently or break entirely.

4. **Lack of automation tools**  
   Managing multiple sweeps and agents across multiple GPUs typically involves writing custom scripts or performing manual, error-prone steps.

**EasySweeps** simplifies and automates these tasks by:
- Creating multiple sweeps from a template and a variants file
- Launching and managing sweep agents across specific GPUs
- Allowing sweep agents to run in isolated copies of the codebase
- Providing easy-to-use commands for status checks and cleanup

This makes large-scale sweep management faster, safer, and less error-prone.


## Installation

```bash
pip install easysweeps
```

## Configuration

Create a `config.yaml` file in your project root:

```yaml
sweep_dir: "sweeps"          # Directory for sweep configurations
agent_log_dir: "agent_logs"  # Directory for agent logs
conda_env: "your_env"        # Your conda environment, this env will be used when running agents
entity: "your_entity"        # W&B entity name
project: "your_project"      # W&B project name, The project folder name
conda_path: "~/anaconda3/etc/profile.d/conda.sh"  # Path to conda.sh, in some machines you can run locate conda

# Project copying configuration
enable_project_copy: false   # Set to true to enable copying project for each agent
project_copy_base_dir: "~/wandb_projects"  # Base directory where project copies will be created
```

## Prerequisites

- Python 3.7 or higher
- Weights & Biases account and API key
- tmux installed on your system
- CUDA-capable GPUs (if using GPU acceleration)
- Conda environment with required packages

## Usage

### 1. Create Sweeps

Create a template file (`sweeps/sweep_template.yaml`)
This file will contain the sweep configuarion - parameters that distinguish different sweeps should be set to None:
```yaml
name: "example_{dataset}"
method: "grid" # can be 
metric:
  name: "loss"
  goal: "minimize"
parameters:
  learning_rate:
    values: [0.0001, 0.001, 0.01]
  weight_decay:
    values: [0.0, 0.0001, 0.001]
  dataset:
    value: None # None values will be replaced with the value in sweep_varaints.yaml
program: "train.py" 
```

Create a variants file (`sweeps/sweep_variants.yaml`):
```yaml
dataset: ['mnist', 'imagenet', 'coco'] # for each dataset a new sweep will be created
```

Create the sweeps:
```bash
ez sweep
```

### 2. Launch Agents

Launch agents for a specific sweep ID on specified GPUs:
```bash
# Show all available sweeps
ez agent --gpu-list 0,1

# Launch agents for sweep abc123 on GPUs 0 and 1
ez agent abc123 --gpu-list 0,1

# Launch 3 agents per GPU for sweep abc123 on GPU 0
ez agent abc123 --gpu-list 0 --agents-per-sweep 3

# Launch agents with force recopy
ez agent abc123 --gpu-list 0,1 --force-recopy
```

The `--agents-per-sweep` option allows you to run multiple agents for the same sweep on each GPU.
Note: When running multiple agents on the same GPU, make sure your model and batch size can fit within the GPU memory.

### 3. Project Copying

When `enable_project_copy` is set to `true` in your `config.yaml`, EasySweeps will create a separate copy of your project for each sweep agent. This is useful when:

- You want to modify code for specific sweeps without affecting others
- You need to maintain different versions of your code for different experiments
- You want to avoid conflicts between agents modifying the same files

The project copies will be created in the directory specified by `project_copy_base_dir`, with each copy named as `{project_name}_{sweep_id}`. The copying process:

- Creates a fresh copy of your project for each sweep
- Excludes unnecessary files (`.git`, `__pycache__`, etc.)
- Maintains the same directory structure
- Preserves all your code and configuration files

By default, if a project directory already exists, EasySweeps will reuse it instead of creating a new copy. If you want to force a fresh copy of the project, you can use the `--force-recopy` flag:

```bash
# Force recopy project directories even if they already exist
ez agent --gpu-list 0 --force-recopy
```

This is particularly useful when:
- You've made changes to your code and want to ensure all agents use the latest version
- You want to start fresh with clean project copies
- You suspect the existing copies might be corrupted or outdated

Example directory structure:
```
~/wandb_projects/
├── your_project_abc123/
│   ├── train.py
│   ├── config.yaml
│   └── ...
├── your_project_def456/
│   ├── train.py
│   ├── config.yaml
│   └── ...
└── ...
```

### 4. Manage GPUs and Server

Kill processes on specific GPUs or the entire server:
```bash
# Kill all processes on a specific GPU
ez kill-all --gpu 0

# Kill all wandb processes on the server
ez kill-all --server

# Force kill without confirmation
ez kill-all --gpu 0 --force
ez kill-all --server --force
```

Show status of all sweeps and agents:
```bash
ez status
```

This command displays a comprehensive status of all sweeps and their agents:
- All created sweeps from your sweep log
- Currently running agents in tmux sessions and windows
- GPU assignments for each agent
- Status of each agent (running/stopped)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

The MIT License is a permissive license that allows for:
- Commercial use
- Modification
- Distribution
- Private use

While providing:
- No liability
- No warranty

For more information about the MIT License, visit [choosealicense.com/licenses/mit/](https://choosealicense.com/licenses/mit/). 
