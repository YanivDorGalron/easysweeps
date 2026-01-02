import pytest
from unittest.mock import patch, Mock
import tempfile
import shutil
from pathlib import Path

from easysweeps.cli import cli


class TestIntegration:
    """Integration tests that test multiple commands working together."""

    def test_full_workflow_sweep_then_agent(self, runner, mock_config, setup_sweep_files, mock_wandb_api):
        """Test the full workflow: create sweeps, then launch agents."""
        files = setup_sweep_files
        
        # Step 1: Create sweeps
        with patch('easysweeps.launch_sweeps.create_sweeps') as mock_create_sweeps:
            mock_create_sweeps.return_value = [
                ("experiment_1", "sweep_abc123"),
                ("experiment_2", "sweep_def456")
            ]
            
            result = runner.invoke(cli, ['sweep'])
            assert result.exit_code == 0
            assert "Successfully created 2 sweeps" in result.output

        # Step 2: Launch agents for first sweep
        with patch('easysweeps.launch_agents.launch_agents') as mock_launch:
            result = runner.invoke(cli, [
                'agent', 'sweep_abc123',
                '--gpu-list', '0', '1'
            ])
            assert result.exit_code == 0
            assert "Successfully launched sweep agents" in result.output

        # Step 3: Check status
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value.stdout = """
wandb-agent-sweep_abc123-0-1.scope                loaded active running User-defined scope
wandb-agent-sweep_abc123-1-1.scope                loaded active running User-defined scope
            """
            
            result = runner.invoke(cli, ['status'])
            assert result.exit_code == 0
            assert "Active Sweeps:" in result.output
            assert "sweep_abc123" in result.output

    def test_agent_list_sweeps_then_launch(self, runner, mock_config, mock_wandb_api):
        """Test listing available sweeps then launching agents."""
        # Step 1: List available sweeps (no sweep ID provided)
        result = runner.invoke(cli, ['agent', '--gpu-list', '0'])
        
        assert result.exit_code == 0
        assert "Available sweeps:" in result.output
        assert "experiment_1" in result.output
        assert "ID: abc123" in result.output

        # Step 2: Launch agents for a specific sweep
        with patch('easysweeps.launch_agents.launch_agents') as mock_launch:
            result = runner.invoke(cli, [
                'agent', 'abc123',
                '--gpu-list', '0'
            ])
            assert result.exit_code == 0

    def test_status_kill_workflow(self, runner, mock_config, mock_wandb_api):
        """Test checking status then killing specific agents."""
        # Step 1: Check status
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value.stdout = """
wandb-agent-abc123-0-1.scope                loaded active running User-defined scope
wandb-agent-abc123-1-1.scope                loaded active running User-defined scope
wandb-agent-def456-0-1.scope                loaded active running User-defined scope
            """
            
            result = runner.invoke(cli, ['status'])
            assert result.exit_code == 0
            assert "abc123" in result.output
            assert "def456" in result.output

        # Step 2: Kill agents for specific sweep
        with patch('subprocess.run') as mock_subprocess:
            result = runner.invoke(cli, ['kill', '--sweep', 'abc123'])
            assert result.exit_code == 0
            assert "Killed all agents for sweep abc123" in result.output

    def test_config_integration(self, runner, temp_dir):
        """Test that config integration works across commands."""
        # Create custom config
        config_data = {
            "entity": "custom-entity",
            "project": "custom-project",
            "sweep_dir": str(temp_dir / "custom_sweeps"),
            "agent_log_dir": str(temp_dir / "custom_logs")
        }
        
        with patch('easysweeps.cli.config') as mock_config:
            mock_config.get.side_effect = lambda key: config_data.get(key)
            
            # Test sweep command uses config
            with patch('easysweeps.launch_sweeps.create_sweeps') as mock_create_sweeps:
                mock_create_sweeps.return_value = []
                
                # This should fail because the sweep directory doesn't exist
                result = runner.invoke(cli, ['sweep'])
                assert result.exit_code != 0
                assert "Template file not found" in result.output
