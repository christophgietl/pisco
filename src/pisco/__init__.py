"""Keyboard-only controller for Sonos speakers."""

import logging.config
from typing import Final

import platformdirs

LOG_FILE: Final = (
    platformdirs.user_log_path(appname="pisco", ensure_exists=True) / "pisco.jsonl"
)

logging.config.dictConfig(
    {
        "disable_existing_loggers": False,
        "formatters": {
            "json_formatter": {
                "class": "pythonjsonlogger.foobar.JsonFormatter",
                "format": (
                    "%(asctime)s %(name)s %(levelname)s "
                    "%(message)s %(thread)s %(threadName)s"
                ),
            }
        },
        "handlers": {
            "rot_file_handler": {
                "backupCount": 9,
                "class": "logging.handlers.RotatingFileHandler",
                "filename": LOG_FILE,
                "formatter": "json_formatter",
                "maxBytes": 1_000_000,
            }
        },
        "root": {"handlers": ["rot_file_handler"], "level": "DEBUG"},
        "version": 1,
    }
)
