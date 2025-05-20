import os
from pathlib import Path
import yaml
import subprocess
import shutil

class Config:
    """Configuration manager for wandb sweep automation"""
    
    def __init__(self, config_file: Path = None):
        self.config_file = config_file or Path("config.yaml")
        self.defaults = {
            "sweep_dir": "sweeps",
            "agent_log_dir": "agent_logs",
            "conda_env": "wandb_sweeps",
            "entity": "yaniv_team",
            "project": self._detect_project_name(),
            "conda_path": self._detect_conda_path(),
        }
        self.config = self._load_config()

    def _detect_project_name(self) -> str:
        """Detect the project name from the current directory"""
        return Path.cwd().name

    def _detect_conda_path(self) -> str:
        """Detect the conda.sh path by checking common locations"""
        # Common conda installation paths
        common_paths = [
            "~/anaconda3/etc/profile.d/conda.sh",
            "~/miniconda3/etc/profile.d/conda.sh",
            "~/miniforge3/etc/profile.d/conda.sh",
            "/opt/anaconda3/etc/profile.d/conda.sh",
            "/opt/miniconda3/etc/profile.d/conda.sh",
            "/opt/miniforge3/etc/profile.d/conda.sh",
        ]
        
        # Check if conda is in PATH
        if shutil.which("conda"):
            try:
                # Get conda installation path
                conda_path = subprocess.check_output(
                    ["conda", "info", "--base"],
                    text=True
                ).strip()
                conda_sh = Path(conda_path) / "etc/profile.d/conda.sh"
                if conda_sh.exists():
                    return str(conda_sh)
            except:
                pass

        # Check common paths
        for path in common_paths:
            expanded_path = Path(path).expanduser()
            if expanded_path.exists():
                return str(expanded_path)

        # If not found, return default
        return "~/anaconda3/etc/profile.d/conda.sh"

    def _load_config(self) -> dict:
        """Load configuration from file or use defaults"""
        if self.config_file.exists():
            with open(self.config_file) as f:
                return {**self.defaults, **yaml.safe_load(f)}
        return self.defaults.copy()

    def get(self, key: str, default=None):
        """Get configuration value, with environment variable override"""
        # Check environment variable first
        env_key = f"WANDB_SWEEP_{key.upper()}"
        if env_key in os.environ:
            return os.environ[env_key]
        
        # Then check config file
        return self.config.get(key, default)

    def save(self):
        """Save current configuration to file"""
        with open(self.config_file, 'w') as f:
            yaml.dump(self.config, f)

# Create global config instance
config = Config() 