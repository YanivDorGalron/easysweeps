import pytest
from unittest.mock import patch, Mock

from easysweeps.cli import cli


class TestStatusCommand:
    """Tests for the status command."""

    def test_status_command_with_active_sweeps(self, runner, mock_config, mock_subprocess, mock_wandb_api):
        """Test status command shows active sweeps correctly."""
        # Mock systemctl output with running agents
        mock_subprocess.return_value.stdout = """
wandb-agent-abc123-0-1.scope                                                                         loaded active running User-defined scope
wandb-agent-abc123-1-1.scope                                                                         loaded active running User-defined scope
wandb-agent-def456-0-1.scope                                                                         loaded active stopped User-defined scope
        """
        
        result = runner.invoke(cli, ['status'])
        
        assert result.exit_code == 0
        assert "Active Sweeps:" in result.output
        assert "experiment_1 (ID: abc123)" in result.output
        assert "[Launched Runs: 5]" not in result.output
        assert "GPU 0 | Agents: A1" in result.output
        assert "GPU 1 | Agents: A1" in result.output

    def test_status_command_with_show_runs(self, runner, mock_config, mock_subprocess, mock_wandb_api):
        """Test status command with --show-runs flag."""
        # Mock systemctl output with running agents
        mock_subprocess.return_value.stdout = """
wandb-agent-abc123-0-1.scope                                                                         loaded active running User-defined scope
        """
        
        result = runner.invoke(cli, ['status', '--show-runs'])
        
        assert result.exit_code == 0
        assert "Active Sweeps:" in result.output
        assert "experiment_1 (ID: abc123) [Launched Runs: 5]" in result.output

    def test_status_command_with_inactive_sweeps(self, runner, mock_config, mock_subprocess, mock_wandb_api):
        """Test status command shows inactive sweeps correctly."""
        # Mock systemctl output with no running agents
        mock_subprocess.return_value.stdout = ""
        
        result = runner.invoke(cli, ['status'])
        
        assert result.exit_code == 0
        assert "Inactive Sweeps (no running agents):" in result.output
        assert "experiment_1 (ID: abc123)" in result.output
        assert "experiment_2 (ID: def456)" in result.output
        assert "[Launched Runs:" not in result.output

    def test_status_command_no_sweeps(self, runner, mock_config, mock_subprocess, mock_wandb_api):
        """Test status command when no sweeps exist."""
        # Mock empty sweeps list
        mock_wandb_api.return_value.project.return_value.sweeps.return_value = []
        mock_subprocess.return_value.stdout = ""
        
        result = runner.invoke(cli, ['status'])
        
        assert result.exit_code == 0
        assert "No W&B sweeps found" in result.output

    def test_status_command_parses_unit_names_correctly(self, runner, mock_config, mock_subprocess, mock_wandb_api):
        """Test that status command correctly parses systemd unit names."""
        # Mock systemctl output with various unit formats
        mock_subprocess.return_value.stdout = """
wandb-agent-abc123-0-1.scope                                                                         loaded active running User-defined scope
wandb-agent-abc123-2-3.scope                                                                         loaded active stopped User-defined scope
wandb-agent-xyz789-1-2.scope                                                                         loaded active running User-defined scope
        """
        
        result = runner.invoke(cli, ['status'])
        
        assert result.exit_code == 0
        # Should parse sweep ID abc123 with GPU 0 agent 1 and GPU 2 agent 3
        assert "abc123" in result.output
        assert "GPU 0 | Agents: A1" in result.output
        assert "GPU 2 | Agents: A3" in result.output

    def test_status_command_handles_malformed_unit_names(self, runner, mock_config, mock_subprocess, mock_wandb_api):
        """Test status command handles malformed unit names gracefully."""
        # Mock systemctl output with malformed unit names
        mock_subprocess.return_value.stdout = """
wandb-agent-malformed.scope                                                                         loaded active running User-defined scope
wandb-agent-abc123-0-1.scope                                                                         loaded active running User-defined scope
some-other-unit.scope                                                                               loaded active running User-defined scope
        """
        
        result = runner.invoke(cli, ['status'])
        
        assert result.exit_code == 0
        # Should still show the valid unit
        assert "abc123" in result.output

    def test_status_command_handles_subprocess_exception(self, runner, mock_config, mock_wandb_api):
        """Test status command handles subprocess exceptions gracefully."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("Subprocess error")
            
            result = runner.invoke(cli, ['status'])
            
            assert result.exit_code != 0
            assert "Subprocess error" in result.output

    def test_status_command_missing_wandb_api(self, runner, mock_config, mock_subprocess):
        """Test status command when W&B API is not available."""
        with patch('wandb.Api') as mock_api:
            mock_api.side_effect = Exception("W&B API error")
            
            result = runner.invoke(cli, ['status'])
            
            assert result.exit_code != 0
            assert "Failed to initialize W&B API" in result.output 