from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from easysweeps.launch_agents import launch_agents as launch_agents_fn

def build_args(tmp_sweep_dir, sweep_id="abc123", gpu_list=None, agents_per=1):
    return SimpleNamespace(
        sweep_log_dir=str(tmp_sweep_dir),
        gpu_list=gpu_list or [0],
        entity="test-entity",
        project="test-project",
        agents_per_sweep=agents_per,
        sweep_id=sweep_id,
        all_gpus=True,
    )

@pytest.fixture
def sweep_log_and_config(monkeypatch, tmp_path):
    # Patch config.get used inside launch_agents
    def fake_get(key, default=None):
        mapping = {
            "agent_log_dir": str(tmp_path / "logs"),
            "entity": "test-entity",
        }
        return mapping.get(key, default)

    monkeypatch.setattr("easysweeps.launch_agents.config.get", fake_get)
    return tmp_path

def test_launch_agents_avoids_occupied_indices(sweep_log_and_config, mock_wandb_api):
    sweep_log_dir = sweep_log_and_config
    args = build_args(sweep_log_dir, gpu_list=[0], agents_per=2)
    
    # Mock systemctl output to show index 0 and 2 are occupied
    # wandb-agent-abc123-0-0.scope
    # wandb-agent-abc123-0-2.scope
    mock_systemctl_output = """
wandb-agent-abc123-0-0.scope loaded active running
wandb-agent-abc123-0-2.scope loaded active running
other-service.service loaded active running
    """
    
    with patch("subprocess.run") as mock_run:
        # First call is to get_occupied_indices
        # Subsequent calls are to launch agents
        
        def side_effect(cmd, **kwargs):
            if isinstance(cmd, list) and 'list-units' in cmd:
                return MagicMock(stdout=mock_systemctl_output)
            return MagicMock()

        mock_run.side_effect = side_effect
        
        launch_agents_fn(args)

    # We expect 2 agents to be launched
    # They should have indices 1 and 3 (since 0 and 2 are occupied)
    
    # Filter calls that are systemd-run (launching agents)
    launch_calls = [c for c in mock_run.call_args_list if isinstance(c[0][0], str) and "systemd-run" in c[0][0]]
    
    assert len(launch_calls) == 2
    
    # First launched agent should have index 1
    assert "--unit=wandb-agent-abc123-0-1" in launch_calls[0][0][0]
    # Second launched agent should have index 3
    assert "--unit=wandb-agent-abc123-0-3" in launch_calls[1][0][0]
