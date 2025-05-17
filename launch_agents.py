import csv
import subprocess
from pathlib import Path

sweep_log = Path("GINPool/sweeps/created_sweeps.txt")
agent_log_dir = Path("agent_logs")
agent_log_dir.mkdir(parents=True, exist_ok=True)

gpu_list = [7, 6, 5, 4, 3, 2, 1, 0]
entity = "yaniv_team"
project = "Explainability"

launch_summary_file = agent_log_dir / "agent_launches.csv"
launch_records = []

with sweep_log.open() as f:
    lines = [line.strip() for line in f if line.strip()]

for i, line in enumerate(lines):
    name, sweep_id = line.split()
    gpu = gpu_list[i % len(gpu_list)]
    log_file = agent_log_dir / f"{name}.log"

    cmd = (
        f'nohup bash -c '
        f'"source ~/anaconda3/etc/profile.d/conda.sh && '
        f'conda activate pool && '
        f'CUDA_VISIBLE_DEVICES={gpu} PYTHONPATH=$PWD '
        f'wandb agent {entity}/{project}/{sweep_id}" '
        f'> {log_file} 2>&1 &'
    )
    print(f"Launching agent for {name} on GPU {gpu}\n{cmd}\n")
    subprocess.run(cmd, shell=True)

    launch_records.append([name, sweep_id, gpu, str(log_file)])

with launch_summary_file.open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["sweep_name", "sweep_id", "gpu", "log_file"])
    writer.writerows(launch_records)
