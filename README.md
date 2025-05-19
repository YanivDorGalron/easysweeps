# EasySweeps

A command-line tool for automating Weights & Biases sweeps across multiple GPUs.

## Features

- Create multiple sweeps from a template and variants configuration
- Launch sweep agents in tmux sessions
- Kill specific sweep agents on specific GPUs
- Comprehensive logging and monitoring

## Installation

```bash
pip install -e .
```

## Configuration

Create a `config.yaml` file:

```yaml
sweep_dir: "sweeps"          # Directory for sweep configurations
agent_log_dir: "agent_logs"  # Directory for agent logs
conda_env: "your_env"        # Your conda environment
entity: "your_entity"        # W&B entity name
project: "your_project"      # W&B project name
conda_path: "~/anaconda3/etc/profile.d/conda.sh"
```

## Usage

### 1. Create Sweeps

Create a template file (`sweeps/sweep_template.yaml`):
```yaml
name: "my_sweep_{param1}_{param2}"
method: "grid"
parameters:
  param1:
    value: null
  param2:
    value: null
```

Create a variants file (`sweeps/sweep_variants.yaml`):
```yaml
param1: ["value1", "value2"]
param2: ["value3", "value4"]
```

Create the sweeps:
```bash
easysweeps sweep
```

### 2. Launch Agents

Launch agents on specific GPUs:
```bash
easysweeps agent --gpu-list 0,1 
```

Launch agents on all specified GPUs for each sweep:
```bash
easysweeps agent --gpu-list 0,1 --all-gpus
```

### 3. Manage Agents

Kill an agent:
```bash
easysweeps kill sweep_id --gpu 0
```

The `kill` command features intelligent sweep ID autocompletion:
- If you don't provide a sweep ID, you'll be prompted to enter one with tab completion
- You can type a partial sweep ID and press tab to see matching options
- If multiple sweeps match your input, you'll see an interactive selection dialog
- The autocompletion is powered by prompt_toolkit and reads from your sweep log file

Example interaction:
```bash
$ easysweeps kill
Enter partial sweep ID: abc<TAB>  # Shows all sweep IDs starting with "abc"
Select sweep ID:                  # If multiple matches, shows interactive dialog
```

Show status of all sweeps and agents:
```bash
easysweeps status
```

This command displays a comprehensive status of all sweeps and their agents:
- All created sweeps from your sweep log
- Currently running agents in tmux sessions and windows
- GPU assignments for each agent
- Status of each agent (running/stopped)


### Command Aliases

EasySweeps can be used with the shorter alias `es`:
```bash
# These commands are equivalent
easysweeps sweep
es sweep

# And these
easysweeps agent --gpu-list 0,1
es agent --gpu-list 0,1

# And these
easysweeps kill sweep_id --gpu 0
es kill sweep_id --gpu 0
```

## Tmux Session Management

EasySweeps uses tmux to manage sweep agents. Here's how it works:

1. **Sessions**: Each sweep gets its own tmux session named after its sweep ID
   - Example: `abc123_gpu0` for sweep ID `abc123` running on GPU 0

2. **Windows**: Each GPU running a sweep agent gets its own window
   - Windows are named `gpu0`, `gpu1`, etc.
   - Each window runs a single sweep agent

3. **Viewing Sessions**:
   ```bash
   # List all tmux sessions
   tmux ls
   
   # Attach to a specific session
   tmux attach -t session_name
   
   # Detach from session (press Ctrl+B, then D)
   ```

4. **Session Cleanup**:
   - When you kill an agent, its window is removed
   - If it's the last window in a session, the entire session is cleaned up
   - All agent output is logged to files in the `agent_log_dir`

## License

MIT License 