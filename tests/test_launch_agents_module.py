from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

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
def sweep_log_and_config(monkeypatch, temp_dir):
    # Prepare directories
    sweep_log_dir = Path(temp_dir) / "sweeps"
    sweep_log_dir.mkdir(parents=True)

    # Patch config.get used inside launch_agents
    def fake_get(key, default=None):
        mapping = {
            "agent_log_dir": str(Path(temp_dir) / "logs"),
        }
        return mapping.get(key, default)

    monkeypatch.setattr("easysweeps.launch_agents.config.get", fake_get)
    return sweep_log_dir


def test_launch_agents_builds_expected_commands(sweep_log_and_config, mock_wandb_api):
    sweep_log_dir = sweep_log_and_config
    args = build_args(sweep_log_dir, gpu_list=[0, 1], agents_per=2)
    expected_calls = len(args.gpu_list) * args.agents_per_sweep

    with patch("subprocess.run") as mock_run:
        launch_agents_fn(args)

    # Filter calls to only include agent launches (ignore systemctl calls from get_occupied_indices)
    launch_calls = [c for c in mock_run.call_args_list if isinstance(c[0][0], str) and "systemd-run" in c[0][0]]

    # subprocess.run should have been called expected_calls times for agent launches
    assert len(launch_calls) == expected_calls

    # Inspect first command for correctness
    first_cmd = launch_calls[0][0][0]
    assert f"--unit=wandb-agent-{args.sweep_id}-0-0" in first_cmd
    assert "CUDA_VISIBLE_DEVICES=0" in first_cmd
