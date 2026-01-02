# FAQ

## General Questions

### How do I log into W&B?
EasySweeps uses your local W&B credentials. If you haven't logged in yet, run:
```bash
wandb login
```

### Can I use a custom config file name?
By default, EasySweeps looks for `ez_config.yaml` in the current directory. Most commands support a `--config` flag to specify a different path.

## Troubleshooting

### My agents are not finding any GPUs
Ensure you have the Nvidia drivers and `nvidia-smi` installed. EasySweeps detects GPUs by their index (0, 1, 2...). If `nvidia-smi` works, `ez agent` should work too.

### How do I see the logs of my agents?
Logs are stored in the directory defined by `agent_log_dir` in your `ez_config.yaml` (default is `agent_logs/`). Each agent has its own log file named after the sweep ID and timestamp.

### I ran `ez kill` but the process is still there
`ez kill` attempts a clean termination first. If a process is stuck, you can use `ez kill --force` to send a SIGKILL.
