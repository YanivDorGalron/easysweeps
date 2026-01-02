import os
import time
from unittest.mock import patch
import pytest
import yaml
import wandb
from pathlib import Path
from click.testing import CliRunner
from easysweeps.cli import cli

# Define the training script that will be run by the agent
FAST_TRAIN_SCRIPT = """
import wandb
import time
import random

def train():
    wandb.init()
    config = wandb.config
    
    # Simulate training loop
    for epoch in range(5):
        loss = 1.0 / (epoch + 1) + random.random() * 0.1
        accuracy = 0.2 * (epoch + 1) + random.random() * 0.05
        
        wandb.log({
            "loss": loss,
            "accuracy": accuracy,
            "epoch": epoch
        })
        time.sleep(1)  # Run for at least a few seconds
        
    wandb.finish()

if __name__ == "__main__":
    train()
"""

# Define the sweep configuration
SWEEP_CONFIG = {
    "name": "live_test_experiment_{learning_rate}",
    "method": "grid",
    "metric": {"name": "loss", "goal": "minimize"},
    "parameters": {
        "learning_rate": {"value": 0.01}
    },
    "program": "fast_train.py"
}

@pytest.fixture
def live_test_setup(tmp_path):
    """Sets up a temporary directory with necessary files for the live test."""
    # Create the training script
    train_path = tmp_path / "fast_train.py"
    with open(train_path, "w") as f:
        f.write(FAST_TRAIN_SCRIPT)
        
    # Create sweep directory and config
    sweep_dir = tmp_path / "sweeps"
    sweep_dir.mkdir()
    
    sweep_config_path = tmp_path / "sweeps" / "sweep_template.yaml"
    with open(sweep_config_path, "w") as f:
        yaml.dump(SWEEP_CONFIG, f)

    # Create variants file - MUST be a dict of lists for Cartesian product
    variants_config = {
        "learning_rate": [0.01]
    }
    variants_path = tmp_path / "sweeps" / "sweep_variants.yaml"
    with open(variants_path, "w") as f:
        yaml.dump(variants_config, f)
        
    # Helper to clean up processes if needed
    yield {
        "root": tmp_path,
        "sweeps": sweep_dir,
        "logs": tmp_path / "agent_logs"
    }

@pytest.mark.integration
class TestLiveWorkflow:
    def test_full_lifecycle(self, live_test_setup):
        """
        Verifies:
        1. Creation of a sweep on WandB.
        2. Launching of an agent locally.
        3. Agent picking up a run.
        4. Run reporting metrics to WandB.
        """
        # Ensure we are logged in
        try:
            api = wandb.Api()
            assert api.api_key, "WandB API key not found. Please run `wandb login` or set WANDB_API_KEY"
            print(f"Using WandB Entity: {api.default_entity}")
        except Exception as e:
            pytest.fail(f"Could not connect to WandB API: {e}")
        
        runner = CliRunner()
        root_dir = live_test_setup["root"]
        
        config_data = {
            "sweep_dir": "sweeps",
            "agent_log_dir": "agent_logs",
            "project": "wandb_sweep_automation_test", # Use a test project
        }
        
        with open(root_dir / "ez_config.yaml", "w") as f:
            yaml.dump(config_data, f)
            
        # We need to ensure the code uses our new config
        # Since 'config' is imported in various modules, we need to patch it where it is used.
        from easysweeps.config import Config
        custom_config = Config(root_dir / "ez_config.yaml")
        
        with patch("easysweeps.cli.config", custom_config), \
             patch("easysweeps.launch_sweeps.config", custom_config), \
             patch("easysweeps.launch_agents.config", custom_config):
             
            # Step 1: Create Sweep
            current_dir = os.getcwd()
            os.chdir(root_dir)
            try:
                print(f"CWD: {os.getcwd()}")
                
                 # Create the sweep
                result = runner.invoke(cli, ['sweep'])
                # If command failed, print output
                if result.exit_code != 0:
                    print(f"Command Output: {result.output}")
            finally:
                os.chdir(current_dir)
            assert result.exit_code == 0, f"Sweep creation failed: {result.output}"
            assert "Successfully created" in result.output
            
            print("Launching agent...")
            
            # Using API to find the sweep we just created
            project = config_data["project"]
            sweeps = api.project(project).sweeps()
            
            target_sweep = None
            for s in sweeps:
                if "live_test_experiment" in s.name:
                    target_sweep = s
                    break
            
            assert target_sweep is not None, "Could not find created sweep in WandB API"
            sweep_id = target_sweep.id
            print(f"Verified sweep created: {sweep_id} ({target_sweep.name})")

            os.chdir(root_dir)
            try:
                result = runner.invoke(cli, ['agent', sweep_id, '--gpu-list', '0', '--agents-per-sweep', '1'])
                if result.exit_code != 0:
                    print(f"Agent launch output: {result.output}")
            finally:
                os.chdir(current_dir)
                
            assert result.exit_code == 0, f"Agent launch failed: {result.output}"
            
            # Step 3: Wait and Verify Execution
            print("Waiting for runs to start...")
            max_retries = 30
            found_run = None
            
            for i in range(max_retries):
                # Refresh sweep object to ensure latest state?
                # query runs explicitly
                runs = api.runs(f"{api.default_entity}/{project}", filters={"sweep": sweep_id})
                if len(runs) > 0:
                    found_run = runs[0] # Pick the first one
                    if found_run.state == "running" or found_run.state == "finished":
                        # Check metrics
                        history = found_run.scan_history()
                        metrics = list(history)
                        if len(metrics) > 0 and 'loss' in metrics[0]:
                            print(f"Found run {found_run.id} with metrics: {metrics[0]}")
                            break
                time.sleep(2)
                
            assert found_run is not None, "No run started for the sweep"
            
            # Verify metrics
            history = list(found_run.scan_history())
            assert len(history) > 0, "Run did not report any history metrics"
            assert 'loss' in history[0], "Run history missing 'loss' metric"
            
            # Step 4: Cleanup
            runner.invoke(cli, ['kill', '--sweep', sweep_id])
