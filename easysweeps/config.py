import os
from pathlib import Path
import yaml

class Config:
    """Configuration manager for wandb sweep automation"""
    
    def __init__(self, config_file: Path = None):
        self.config_file = config_file or Path("config.yaml")
        self.defaults = {
            "sweep_dir": "sweeps",
            "agent_log_dir": "agent_logs",
            "conda_env": "pool",
            "entity": "yaniv_team",
            "project": "Explainability",
            "conda_path": "~/anaconda3/etc/profile.d/conda.sh",
        }
        self.config = self._load_config()

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