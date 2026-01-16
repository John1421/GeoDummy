import logging
from unittest.mock import patch

from App.LogManager import LogManager


class DummyApp:
    """Minimal stand‑in for Flask app with a logger attribute."""
    def __init__(self) -> None:
        self.logger = logging.getLogger("dummy-app")


class TestLogManager:
    def test_configure_logger_file_only(self) -> None:
        """
        disable_console=True, disable_werkzeug=False:
        - Only file handler is added.
        - Logger level and propagate set.
        """
        app = DummyApp()
        # ensure starting with no handlers
        app.logger.handlers.clear()

        lm = LogManager(
            log_file="test.log",
            max_bytes=1234,
            backup_count=3,
            level=logging.DEBUG,
            disable_console=True,
            disable_werkzeug=False,
        )

        with patch("App.LogManager.RotatingFileHandler") as mock_rfh:
            file_handler_instance = mock_rfh.return_value

            returned = lm.configure_flask_logger(app)

        # RotatingFileHandler constructed once
        mock_rfh.assert_called_once()
        args, kwargs = mock_rfh.call_args
        assert str(args[0]).endswith("test.log")
        assert kwargs["maxBytes"] == 1234
        assert kwargs["backupCount"] == 3

        # Returned handler is the same instance
        assert returned is file_handler_instance

        # Only one handler (file) on logger
        assert app.logger.handlers == [file_handler_instance]
        assert app.logger.level == logging.DEBUG
        assert app.logger.propagate is False

    def test_configure_logger_with_console_and_disable_werkzeug(self) -> None:
        """
        disable_console=False, disable_werkzeug=True:
        - Console (StreamHandler) and file handler added.
        - Werkzeug logger disabled.
        """
        app = DummyApp()
        app.logger.handlers.clear()

        lm = LogManager(
            log_file="test_console.log",
            max_bytes=4096,
            backup_count=1,
            level=logging.INFO,
            disable_console=False,
            disable_werkzeug=True,
        )

        with patch("App.LogManager.RotatingFileHandler") as mock_rfh, \
             patch("App.LogManager.logging.StreamHandler") as mock_stream_handler, \
             patch("App.LogManager.logging.getLogger") as mock_get_logger:

            file_handler_instance = mock_rfh.return_value
            console_handler_instance = mock_stream_handler.return_value

            # make getLogger('werkzeug') return a real logger object we can inspect
            werkzeug_logger = logging.getLogger("werkzeug-test")
            def _get_logger(name: str) -> logging.Logger:
                if name == "werkzeug":
                    return werkzeug_logger
                return logging.getLogger(name)

            mock_get_logger.side_effect = _get_logger

            returned = lm.configure_flask_logger(app)

        # File handler is returned and attached
        assert returned is file_handler_instance
        assert file_handler_instance in app.logger.handlers

        # Console handler created and attached
        mock_stream_handler.assert_called_once()
        assert console_handler_instance in app.logger.handlers
        console_handler_instance.setLevel.assert_called_once_with(logging.INFO)

        # Werkzeug logger disabled
        assert werkzeug_logger.disabled is True

    def test_configure_logger_clears_existing_handlers(self) -> None:
        """
        Existing handlers are cleared before configuring new ones.
        """
        app = DummyApp()
        dummy_handler = logging.StreamHandler()
        app.logger.addHandler(dummy_handler)

        lm = LogManager(disable_console=True, disable_werkzeug=False)

        with patch("App.LogManager.RotatingFileHandler") as mock_rfh:
            new_handler = mock_rfh.return_value
            lm.configure_flask_logger(app)

        # Old handler removed, new added
        assert dummy_handler not in app.logger.handlers
        assert new_handler in app.logger.handlers
