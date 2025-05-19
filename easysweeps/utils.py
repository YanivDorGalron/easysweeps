import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

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