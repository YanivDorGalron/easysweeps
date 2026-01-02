import pytest
from unittest.mock import patch, Mock
from click.testing import CliRunner
from pathlib import Path

from easysweeps.cli import cli


class TestSweepCommand:
    """Tests for the sweep command."""

    def test_sweep_command_success(self, runner, mock_config, setup_sweep_files):
        """Test successful sweep creation."""
        files = setup_sweep_files
        
        with patch('easysweeps.launch_sweeps.create_sweeps') as mock_create_sweeps:
            mock_create_sweeps.return_value = [
                ("experiment_1", "sweep_abc123"),
                ("experiment_2", "sweep_def456")
            ]
            
            result = runner.invoke(cli, ['sweep'])
            
            assert result.exit_code == 0
            assert "Successfully created 2 sweeps" in result.output
            mock_create_sweeps.assert_called_once()

    def test_sweep_command_with_custom_paths(self, runner, mock_config, setup_sweep_files):
        """Test sweep command with custom file paths."""
        files = setup_sweep_files
        
        with patch('easysweeps.launch_sweeps.create_sweeps') as mock_create_sweeps:
            mock_create_sweeps.return_value = [("test", "sweep_123")]
            
            result = runner.invoke(cli, [
                'sweep',
                '--sweep-dir', str(files['sweep_dir']),
                '--template', str(files['template_file']),
                '--variants', str(files['variants_file'])
            ])
            
            assert result.exit_code == 0
            mock_create_sweeps.assert_called_once()

    def test_sweep_command_missing_template_file(self, runner, mock_config, temp_dir):
        """Test sweep command fails when template file is missing."""
        result = runner.invoke(cli, [
            'sweep',
            '--sweep-dir', str(temp_dir),
            '--template', str(temp_dir / 'nonexistent.yaml'),
            '--variants', str(temp_dir / 'variants.yaml')
        ])
        
        assert result.exit_code != 0
        assert "Template file not found" in result.output

    def test_sweep_command_missing_variants_file(self, runner, mock_config, temp_dir, sample_sweep_template):
        """Test sweep command fails when variants file is missing."""
        # Create only template file
        template_file = temp_dir / 'template.yaml'
        template_file.write_text("test: config")
        
        result = runner.invoke(cli, [
            'sweep',
            '--sweep-dir', str(temp_dir),
            '--template', str(template_file),
            '--variants', str(temp_dir / 'nonexistent.yaml')
        ])
        
        assert result.exit_code != 0
        assert "Variants file not found" in result.output

    def test_sweep_command_handles_exception(self, runner, mock_config, setup_sweep_files):
        """Test sweep command handles exceptions gracefully."""
        with patch('easysweeps.launch_sweeps.create_sweeps') as mock_create_sweeps:
            mock_create_sweeps.side_effect = Exception("Test error")
            
            result = runner.invoke(cli, ['sweep'])
            
            assert result.exit_code != 0
            assert "Test error" in result.output 