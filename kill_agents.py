import csv
import os
import signal
import subprocess
from pathlib import Path

csv_path = Path("GINPool/sweeps/agent_launches.csv")
keep_logs = True  # Set to False if you want to delete the log files too

# Load sweep metadata
with csv_path.open() as f:
    reader = csv.DictReader(f)
    records = list(reader)

# Store surviving records in case some fail to be killed
surviving_records = []

for record in records:
    sweep_id = record["sweep_id"]
    sweep_name = record["sweep_name"]
    log_file = record["log_file"]

    # Find matching wandb agent processes
    try:
        result = subprocess.check_output(
            ["pgrep", "-f", f"wandb agent.*{sweep_id}"],
            text=True
        )
        pids = result.strip().splitlines()

        for pid in pids:
            print(f"Killing {sweep_name} (PID {pid})")
            os.kill(int(pid), signal.SIGTERM)

        # Optionally delete log file
        if not keep_logs:
            log_path = Path(log_file)
            if log_path.exists():
                log_path.unlink()

    except subprocess.CalledProcessError:
        print(f"No running agent found for sweep: {sweep_name}")
        # You can choose to preserve or remove these
        surviving_records.append(record)

# Overwrite CSV with surviving (not killed) entries
with csv_path.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["sweep_name", "sweep_id", "gpu", "log_file"])
    writer.writeheader()
    writer.writerows(surviving_records)

print("\n✅ Sweep agent cleanup complete.")
