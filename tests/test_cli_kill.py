import pytest
from unittest.mock import patch, Mock

from easysweeps.cli import cli


class TestKillCommand:
    """Tests for the kill command."""

    def test_kill_command_force_with_confirmation(self, runner, mock_config, mock_subprocess):
        """Test kill command with --force flag and user confirmation."""
        result = runner.invoke(cli, ['kill', '--force'], input='y\n')
        
        assert result.exit_code == 0
        assert "Killed all wandb agent units" in result.output
        mock_subprocess.assert_called()

    def test_kill_command_force_without_confirmation(self, runner, mock_config, mock_subprocess):
        """Test kill command with --force flag but user declines."""
        result = runner.invoke(cli, ['kill', '--force'], input='n\n')
        
        assert result.exit_code == 0
        # Should not call systemctl when user declines
        assert "Killed all wandb agent units" not in result.output

    def test_kill_command_specific_gpu(self, runner, mock_config, mock_subprocess):
        """Test kill command targeting specific GPU."""
        # Mock systemctl list-units output
        mock_subprocess.return_value.stdout = """
wandb-agent-abc123-0-1.scope                     loaded active running User-defined scope
wandb-agent-abc123-1-2.scope                     loaded active running User-defined scope
wandb-agent-def456-0-3.scope                     loaded active running User-defined scope
        """
        
        result = runner.invoke(cli, ['kill', '--gpu', '0'])
        
        assert result.exit_code == 0
        assert "Killed all agents on GPU 0" in result.output
        
        # Should have called systemctl stop for the GPU 0 units
        calls = mock_subprocess.call_args_list
        assert any('stop' in str(call) for call in calls)

    def test_kill_command_specific_sweep(self, runner, mock_config, mock_subprocess):
        """Test kill command targeting specific sweep."""
        result = runner.invoke(cli, ['kill', '--sweep', 'abc123'])
        
        assert result.exit_code == 0
        assert "Killed all agents for sweep abc123" in result.output
        
        # Should call systemctl stop with the sweep pattern
        mock_subprocess.assert_called()

    def test_kill_command_specific_sweep_and_gpu(self, runner, mock_config, mock_subprocess):
        """Test kill command targeting specific sweep and GPU."""
        result = runner.invoke(cli, ['kill', '--sweep', 'abc123', '--gpu', '0'])
        
        assert result.exit_code == 0
        assert "Killed agents for abc123 on GPU 0" in result.output

    def test_kill_command_no_options_shows_active_sweeps(self, runner, mock_config, mock_subprocess):
        """Test kill command without options shows active sweeps."""
        # Mock systemctl output with running agents
        mock_subprocess.return_value.stdout = """
wandb-agent-abc123-0-1.scope                     loaded active running User-defined scope
wandb-agent-def456-1-2.scope                     loaded active running User-defined scope
        """
        
        result = runner.invoke(cli, ['kill'])
        
        assert result.exit_code == 0
        assert "Active sweeps:" in result.output
        assert "abc123" in result.output
        assert "def456" in result.output

    def test_kill_command_no_active_sweeps(self, runner, mock_config, mock_subprocess):
        """Test kill command when no sweeps are active."""
        mock_subprocess.return_value.stdout = ""
        
        result = runner.invoke(cli, ['kill'])
        
        assert result.exit_code == 0
        assert "No active sweeps found" in result.output

    def test_kill_command_handles_malformed_unit_names(self, runner, mock_config, mock_subprocess):
        """Test kill command handles malformed unit names gracefully."""
        mock_subprocess.return_value.stdout = """
wandb-agent-malformed.scope                       loaded active running User-defined scope
wandb-agent-abc123-0-1.scope                     loaded active running User-defined scope
other-unit.scope                                  loaded active running User-defined scope
        """
        
        result = runner.invoke(cli, ['kill'])
        
        assert result.exit_code == 0
        # Should only show valid sweep IDs
        assert "abc123" in result.output
        assert "malformed" not in result.output

    def test_kill_command_handles_subprocess_exception(self, runner, mock_config):
        """Test kill command handles subprocess exceptions gracefully."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("Subprocess error")
            
            result = runner.invoke(cli, ['kill', '--gpu', '0'])
            
            assert result.exit_code != 0
            assert "Subprocess error" in result.output

    def test_kill_command_gpu_filtering_logic(self, runner, mock_config, mock_subprocess):
        """Test the GPU filtering logic works correctly."""
        # Set up mock to be called multiple times (list-units, then stop)
        mock_subprocess.return_value.stdout = """
wandb-agent-abc123-0-1.scope                     loaded active running User-defined scope
wandb-agent-abc123-1-2.scope                     loaded active running User-defined scope
wandb-agent-def456-0-3.scope                     loaded active running User-defined scope
        """
        
        result = runner.invoke(cli, ['kill', '--gpu', '0'])
        
        assert result.exit_code == 0
        
        # Should have made multiple calls to subprocess.run
        # First for listing units, then for stopping specific ones
        assert mock_subprocess.call_count >= 2

    def test_kill_command_sweep_pattern_construction(self, runner, mock_config, mock_subprocess):
        """Test that sweep patterns are constructed correctly."""
        result = runner.invoke(cli, ['kill', '--sweep', 'test_sweep_123'])
        
        assert result.exit_code == 0
        
        # Check that systemctl was called with the right pattern
        calls = mock_subprocess.call_args_list
        stop_call = next((call for call in calls if 'stop' in str(call)), None)
        assert stop_call is not None 