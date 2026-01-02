import os
import tempfile
import shutil
from pathlib import Path
import logging
from unittest.mock import patch

import pytest

from easysweeps.config import Config
from easysweeps.utils import setup_logging


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


class TestConfig:
    """Unit tests for easysweeps.config.Config"""

    def test_env_override(self, temp_dir):
        """Environment variables should override config file and defaults."""
        cfg_path = Path(temp_dir) / "ez_config.yaml"
        cfg_path.write_text("entity: file-entity\n")

        # Set environment variable to override entity
        os.environ["WANDB_SWEEP_ENTITY"] = "env-entity"
        try:
            cfg = Config(config_file=cfg_path)
            assert cfg.get("entity") == "env-entity"
        finally:
            os.environ.pop("WANDB_SWEEP_ENTITY", None)

    def test_save_and_reload(self, temp_dir):
        """Config.save should persist changes that are readable by a new instance."""
        cfg_path = Path(temp_dir) / "my_cfg.yaml"
        cfg = Config(config_file=cfg_path)
        cfg.config["entity"] = "persisted-entity"
        cfg.save()

        # New instance should read the persisted value
        cfg2 = Config(config_file=cfg_path)
        assert cfg2.get("entity") == "persisted-entity"


class TestUtils:
    """Unit tests for easysweeps.utils helpers"""

    def test_setup_logging_idempotent(self, temp_dir):
        log_dir = Path(temp_dir) / "logs"

        # Backup and clear existing handlers on root logger
        root_logger = logging.getLogger()
        old_handlers = list(root_logger.handlers)
        root_logger.handlers.clear()
        try:
            setup_logging(log_dir)
            handler_count_after_first = len(root_logger.handlers)

            # Force a log to ensure the lazy file handler creates the file
            logging.info("Initializing logging test")

            # Calling again should NOT add more handlers
            setup_logging(log_dir)
            handler_count_after_second = len(root_logger.handlers)

            assert handler_count_after_first == 2  # file + console
            assert handler_count_after_second == 2
            # Log file should exist
            assert (log_dir / "wandb_sweep.log").exists()
        finally:
            # Restore original handlers to avoid side-effects on other tests
            root_logger.handlers.clear()
            root_logger.handlers.extend(old_handlers)