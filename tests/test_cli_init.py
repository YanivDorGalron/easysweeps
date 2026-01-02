import pytest
from pathlib import Path
from click.testing import CliRunner
from easysweeps.cli import cli
import shutil

class TestInit:
    """Tests for the `ez init` command."""

    @pytest.fixture
    def clean_env(self):
        """Fixture to ensure we are running in a clean directory."""
        # We can't easily change CWD safely in tests running in parallel or same process, 
        # so we will use runner.isolated_filesystem()
        pass

    def test_init_creates_files(self, runner):
        """Test that init command creates necessary files and directories."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ['init'])
            
            assert result.exit_code == 0
            assert "Initialization complete" in result.output
            
            # Check ez_config.yaml
            config_path = Path("ez_config.yaml")
            assert config_path.exists()
            assert 'sweep_dir: "sweeps"' in config_path.read_text()
            
            # Check sweeps directory
            sweeps_dir = Path("sweeps")
            assert sweeps_dir.exists()
            assert sweeps_dir.is_dir()
            
            # Check template file
            template_path = sweeps_dir / "sweep_template.yaml"
            assert template_path.exists()
            assert 'name: "example_sweep_{dataset}"' in template_path.read_text()
            
            # Check variants file
            variants_path = sweeps_dir / "sweep_variants.yaml"
            assert variants_path.exists()
            assert "dataset: ['mnist', 'cifar10']" in variants_path.read_text()

    def test_init_skips_existing_files(self, runner):
        """Test that init command does not overwrite existing files."""
        with runner.isolated_filesystem():
            # Create a dummy config file
            Path("ez_config.yaml").write_text("dummy: content")
            
            result = runner.invoke(cli, ['init'])
            
            assert result.exit_code == 0
            assert "ez_config.yaml already exists, skipping" in result.output
            
            # Verify content wasn't changed
            assert Path("ez_config.yaml").read_text() == "dummy: content"
            
            # Verify other files were still created
            assert Path("sweeps/sweep_template.yaml").exists()

