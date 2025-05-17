import csv
import subprocess
import argparse
from pathlib import Path

def parse_args():
    parser = argparse.ArgumentParser(description='Launch wandb sweep agents')
    parser.add_argument('--conda_env', type=str, default="pool",
                      help='Name of conda environment to use (default: pool)')
    parser.add_argument('--sweep_log_dir', type=str, default="sweeps/",
                      help='Directory containing sweep logs (default: sweeps/)')
    parser.add_argument('--gpu_list', type=int, nargs='+', 
                      default=list(range(len(subprocess.check_output(['nvidia-smi', '--list-gpus']).decode().split('\n')) - 1)),
                      help='List of GPU indices to use (default: all available GPUs)')
    parser.add_argument('--entity', type=str, default="yaniv_team",
                      help='Wandb entity name (default: yaniv_team)')
    parser.add_argument('--project', type=str, default="Explainability",
                      help='Wandb project name (default: Explainability)')
    return parser.parse_args()

args = parse_args()
print(args)
exit()
sweep_log = Path(args.sweep_log_dir + "created_sweeps.txt")
agent_log_dir = Path("agent_logs")
agent_log_dir.mkdir(parents=True, exist_ok=True)

launch_summary_file = agent_log_dir / "agent_launches.csv"
launch_records = []

with sweep_log.open() as f:
    lines = [line.strip() for line in f if line.strip()]

for i, line in enumerate(lines):
    name, sweep_id = line.split()
    gpu = args.gpu_list[i % len(args.gpu_list)]
    log_file = agent_log_dir / f"{name}.log"

    cmd = (
        f'nohup bash -c '
        f'"source ~/anaconda3/etc/profile.d/conda.sh && '
        f'conda activate {args.conda_env} && '
        f'CUDA_VISIBLE_DEVICES={gpu} PYTHONPATH=$PWD '
        f'wandb agent {args.entity}/{args.project}/{sweep_id}" '
        f'> {log_file} 2>&1 &'
    )
    print(f"Launching agent for {name} on GPU {gpu}\n{cmd}\n")
    subprocess.run(cmd, shell=True)

    launch_records.append([name, sweep_id, gpu, str(log_file)])

with launch_summary_file.open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["sweep_name", "sweep_id", "gpu", "log_file"])
    writer.writerows(launch_records)
