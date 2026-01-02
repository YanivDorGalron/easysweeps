import os
from pathlib import Path
import yaml
import subprocess
import wandb

class Config:
    """Configuration manager for wandb sweep automation"""
    
    def __init__(self, config_file: Path = None):
        self.config_file = config_file or Path("ez_config.yaml")
        # 'entity' must be explicitly provided by the user; no default is set here
        self.defaults = {
            "sweep_dir": "sweeps",
            "agent_log_dir": "agent_logs",
            "project": self._detect_project_name(),
        }
        self.config = self._load_config()

    def _detect_project_name(self) -> str:
        """Detect the project name from the current directory"""
        return Path.cwd().name

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
        value = self.config.get(key, default)
        
        # If key is 'entity' and value is None, use wandb's default entity
        if key == 'entity' and (value == 'None' or value is None):
            value = wandb.api.default_entity
        
        return value

    def save(self):
        """Save current configuration to file"""
        with open(self.config_file, 'w') as f:
            yaml.dump(self.config, f)

# Create global config instance
config = Config() 