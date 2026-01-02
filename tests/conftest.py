import pytest
import tempfile
import shutil
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import Mock, patch
import yaml

from easysweeps.cli import cli


@pytest.fixture
def runner():
    """Provides a Click test runner."""
    return CliRunner()


@pytest.fixture
def temp_dir():
    """Provides a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_config(temp_dir):
    """Provides a mock config for testing."""
    config_data = {
        "entity": "test-entity",
        "project": "test-project", 
        "sweep_dir": str(temp_dir / "sweeps"),
        "agent_log_dir": str(temp_dir / "logs")
    }
    
    with patch('easysweeps.cli.config') as mock_config:
        mock_config.get.side_effect = lambda key: config_data.get(key)
        yield mock_config


@pytest.fixture
def sample_sweep_template():
    """Provides a sample sweep template configuration."""
    return {
        "method": "bayes",
        "metric": {"name": "accuracy", "goal": "maximize"},
        "parameters": {
            "learning_rate": {"min": 0.0001, "max": 0.1},
            "batch_size": {"values": [16, 32, 64]}
        }
    }


@pytest.fixture
def sample_sweep_variants():
    """Provides sample sweep variants configuration."""
    return {
        "variants": [
            {"name": "experiment_1", "dataset": "cifar10"},
            {"name": "experiment_2", "dataset": "imagenet"}
        ]
    }


@pytest.fixture
def setup_sweep_files(temp_dir, sample_sweep_template, sample_sweep_variants):
    """Sets up the sweep configuration files in temp directory."""
    sweep_dir = temp_dir / "sweeps"
    sweep_dir.mkdir(parents=True, exist_ok=True)
    
    # Create template file
    template_file = sweep_dir / "sweep_template.yaml"
    with template_file.open('w') as f:
        yaml.dump(sample_sweep_template, f)
    
    # Create variants file
    variants_file = sweep_dir / "sweep_variants.yaml"
    with variants_file.open('w') as f:
        yaml.dump(sample_sweep_variants, f)
    
    return {
        "sweep_dir": sweep_dir,
        "template_file": template_file,
        "variants_file": variants_file
    }


@pytest.fixture
def mock_wandb():
    """Provides mocked wandb functionality."""
    with patch('wandb.sweep') as mock_sweep, \
         patch('wandb.agent') as mock_agent:
        mock_sweep.return_value = "test_sweep_id_123"
        yield {
            "sweep": mock_sweep,
            "agent": mock_agent
        }


@pytest.fixture
def mock_subprocess():
    """Provides mocked subprocess functionality for systemctl commands."""
    with patch('subprocess.run') as mock_run:
        # Default successful result
        mock_run.return_value.stdout = ""
        mock_run.return_value.returncode = 0
        yield mock_run


@pytest.fixture
def mock_wandb_api():
    """Provides mocked wandb API functionality."""
    with patch('wandb.Api') as mock_api:
        # Create mock sweep objects
        mock_sweep1 = Mock()
        mock_sweep1.name = "experiment_1"
        mock_sweep1.id = "abc123"
        mock_sweep1.runs = [Mock()] * 5
        
        mock_sweep2 = Mock()
        mock_sweep2.name = "experiment_2"
        mock_sweep2.id = "def456"
        mock_sweep2.runs = [Mock()] * 10
        
        # Mock the project's sweeps method
        mock_project = Mock()
        mock_project.sweeps.return_value = [mock_sweep1, mock_sweep2]
        
        # Mock the api.project method
        mock_api.return_value.project.return_value = mock_project
        
        # Mock the api.sweep method
        mock_api.return_value.sweep.side_effect = lambda x: next(
            (s for s in [mock_sweep1, mock_sweep2] if s.id in x),
            None
        )
        
        yield mock_api
