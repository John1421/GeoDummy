import logging
from logging.handlers import RotatingFileHandler
import os

class LogManager:
    def __init__(
        self,
        log_file="./logs/app.log",
        max_bytes=10 * 1024 * 1024,
        backup_count=5,
        level=logging.INFO,
        disable_console=True,
    ):
        self.log_file = log_file
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.level = level
        self.disable_console = disable_console

        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)

    def configure_flask_logger(self, app):
        # Remove existing handlers (console, etc.)
        app.logger.handlers.clear()
        app.logger.setLevel(self.level)
        app.logger.propagate = False

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