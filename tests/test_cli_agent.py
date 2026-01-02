import pytest
from unittest.mock import patch, Mock
from pathlib import Path

from easysweeps.cli import cli


class TestAgentCommand:
    """Tests for the agent command."""

    def test_agent_command_success(self, runner, mock_config, mock_wandb_api):
        """Test successful agent launch."""
        with patch('easysweeps.launch_agents.launch_agents') as mock_launch:
            result = runner.invoke(cli, [
                'agent', 'abc123', '--gpu-list', '0'
            ])
            
            assert result.exit_code == 0
            assert "Successfully launched sweep agents" in result.output
            mock_launch.assert_called_once()

    def test_agent_command_with_multiple_agents_per_sweep(self, runner, mock_config, mock_wandb_api):
        """Test agent launch with multiple agents per sweep."""
        with patch('easysweeps.launch_agents.launch_agents') as mock_launch:
            result = runner.invoke(cli, [
                'agent', 'abc123', '--gpu-list', '0',
                '--agents-per-sweep', '3'
            ])
            
            assert result.exit_code == 0
            assert "Successfully launched sweep agents" in result.output
            mock_launch.assert_called_once()

    def test_agent_command_invalid_gpu_list(self, runner, mock_config):
        """Test agent command with invalid GPU list format."""
        result = runner.invoke(cli, [
            'agent', 'abc123', '--gpu-list', 'invalid'
        ])
        
        assert result.exit_code != 0
        assert "Invalid value for '--gpu-list'" in result.output

    def test_agent_command_missing_gpu_list(self, runner, mock_config):
        """Test agent command fails when GPU list is not provided."""
        result = runner.invoke(cli, [
            'agent', 'abc123'
        ])
        
        assert result.exit_code != 0
        assert "--gpu-list is required when launching agents" in result.output

    def test_agent_command_no_sweep_id_shows_available_sweeps(self, runner, mock_config, mock_wandb_api):
        """Test that agent command without sweep ID shows available sweeps."""
        result = runner.invoke(cli, [
            'agent'
        ])
        assert result.exit_code == 0
        assert "Available sweeps:" in result.output

    def test_agent_command_handles_exception(self, runner, mock_config, mock_wandb_api):
        """Test agent command handles exceptions gracefully."""
        with patch('easysweeps.launch_agents.launch_agents') as mock_launch:
            mock_launch.side_effect = Exception("Test error")
            
            result = runner.invoke(cli, [
                'agent', 'abc123', '--gpu-list', '0'
            ])
            
            assert result.exit_code != 0
            assert "Test error" in result.output

    def test_agent_command_args_construction(self, runner, mock_config, mock_wandb_api):
        """Test that agent command constructs arguments correctly."""
        with patch('easysweeps.launch_agents.launch_agents') as mock_launch:
            # Test space-separated GPUs with --gpu-list flag
            result = runner.invoke(cli, [
                'agent', 'abc123', '--gpu-list', '0', '1',
                '--agents-per-sweep', '2'
            ])
            
            assert result.exit_code == 0
            
            # Check that launch_agents was called with correct args
            args = mock_launch.call_args[0][0]
            assert args.sweep_id == 'abc123'
            assert args.gpu_list == [0, 1]
            assert args.agents_per_sweep == 2

    def test_agent_command_repeated_flags(self, runner, mock_config, mock_wandb_api):
        """Test that agent command handles repeated -g flags."""
        with patch('easysweeps.launch_agents.launch_agents') as mock_launch:
            result = runner.invoke(cli, [
                'agent', 'abc123',
                '-g', '0', '-g', '1'
            ])
            
            assert result.exit_code == 0
            args = mock_launch.call_args[0][0]
            assert args.gpu_list == [0, 1]
