"""
Log manager module.

Provides centralized configuration for application logging,
including file rotation and optional console and Werkzeug logging.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from .FileManager import FileManager

file_manager = FileManager()

class LogManager:
    """
    Configures logging for a Flask application using rotating file handlers.
    """

    def __init__(
        self,
        log_file="app.log",
        max_bytes=10 * 1024 * 1024,
        backup_count=5,
        level=logging.INFO,
        disable_console=True,
        disable_werkzeug=False
    ):
        """
        Initialize the LogManager.

        :param log_file: Log file name.
        :param max_bytes: Maximum size of a log file before rotation.
        :param backup_count: Number of rotated log files to keep.
        :param level: Logging level.
        :param disable_console: Disable console logging if True.
        :param disable_werkzeug: Disable Werkzeug logging if True.
        :param file_manager: Optional FileManager instance.
        """

        self.log_file = os.path.join(file_manager.logs_dir, log_file)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.level = level
        self.disable_console = disable_console
        self.disable_werkzeug = disable_werkzeug

    def configure_flask_logger(self, app):
        """
        Configure Flask's logger with file rotation and optional console output.

        :param app: Flask application instance.
        :return: Configured RotatingFileHandler.
        """

        # Remove existing handlers (console, etc.)
        app.logger.handlers.clear()
        app.logger.setLevel(self.level)
        app.logger.propagate = False

        if not self.disable_console:
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.level)
            formatter = logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s"
            )
            console_handler.setFormatter(formatter)
            app.logger.addHandler(console_handler)

        if self.disable_werkzeug:
            # Disable Werkzeug logger
            werkzeug_logger = logging.getLogger('werkzeug')
            werkzeug_logger.disabled = True

        # File handler
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count
        )

        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(self.level)

        app.logger.addHandler(file_handler)


        return file_handler
