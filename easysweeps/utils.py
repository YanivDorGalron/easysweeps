import logging
import sys
import shutil
from pathlib import Path
from logging.handlers import RotatingFileHandler
from .config import config

def setup_logging(log_dir: Path = Path("logs"), level=logging.INFO):
    """Set up logging configuration"""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "wandb_sweep.log"

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )

    # Create handlers
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)

    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Create logger for this package
    logger = logging.getLogger('wandb_sweep_automation')
    return logger

def copy_project_for_sweep(sweep_id: str, base_dir: Path) -> Path:
    """Copy the project directory to a new location for a specific sweep.
    
    Args:
        sweep_id: The sweep ID to use in the directory name
        base_dir: The base directory where the project copy will be created
        
    Returns:
        Path to the new project directory
    """
    logger = logging.getLogger(__name__)
    
    # Expand the home directory if present
    base_dir = Path(base_dir).expanduser()
    
    # Get the project name from config
    project_name = config.get("project")
    
    # Create the target directory with project name and sweep ID
    target_dir = base_dir / f"{project_name}_{sweep_id}"
    if target_dir.exists():
        logger.warning(f"Target directory {target_dir} already exists, removing it")
        shutil.rmtree(target_dir)
    
    # Get the current project directory (where the script is running from)
    current_dir = Path.cwd()
    
    # Copy the project directory
    try:
        shutil.copytree(current_dir, target_dir, 
                       ignore=shutil.ignore_patterns(
                           '.git', '__pycache__', '*.pyc', 
                           '*.pyo', '*.pyd', '.pytest_cache',
                           '*.egg-info', 'dist', 'build'
                       ))
        logger.info(f"Successfully copied project to {target_dir}")
        return target_dir
    except Exception as e:
        logger.error(f"Failed to copy project: {e}")
        raise 