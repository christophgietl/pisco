"""Keyboard-only controller for Sonos speakers."""

import logging.config
from typing import Final

import xdg

LOG_FILE: Final = xdg.XDG_DATA_HOME / "pisco" / "logs" / "pisco.jsonl"
LOG_FILE.parent.mkdir(exist_ok=True, parents=True)

LOG_FORMAT: Final = (
    "%(asctime)s %(name)s %(levelname)s %(message)s %(thread)s %(threadName)s"
)

logging.config.dictConfig(
    {
        "disable_existing_loggers": False,
        "formatters": {
            "json_formatter": {
                "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": LOG_FORMAT,
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
