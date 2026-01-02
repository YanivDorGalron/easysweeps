import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from .config import config


class LazyRotatingFileHandler(RotatingFileHandler):
    """A RotatingFileHandler that only creates the directory and file on first log write."""
    
    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, encoding=None):
        self._log_dir = Path(filename).parent
        self._dir_created = False
        # Use delay=True to prevent file creation until first emit
        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay=True)
    
    def emit(self, record):
        # Create directory only when we actually need to log
        if not self._dir_created:
            self._log_dir.mkdir(parents=True, exist_ok=True)
            self._dir_created = True
        super().emit(record)


def setup_logging(log_dir: Path = Path("logs"), level=logging.INFO):
    """Set up logging configuration"""
    # Check if root logger already has handlers
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return logging.getLogger('wandb_sweep_automation')

    log_file = log_dir / "wandb_sweep.log"

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )

    # Create handlers - use LazyRotatingFileHandler to delay file creation
    file_handler = LazyRotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)

    # Setup root logger
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Create logger for this package
    logger = logging.getLogger('wandb_sweep_automation')
    return logger