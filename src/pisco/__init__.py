"""Keyboard-only controller for Sonos speakers."""


import logging.config
import pathlib
from typing import Final

import xdg

_LOG_FILE: Final[pathlib.Path] = xdg.XDG_DATA_HOME / "pisco" / "logs" / "pisco.jsonl"
_LOG_FILE.parent.mkdir(exist_ok=True, parents=True)

_LOG_FORMAT: Final[
    str
] = "%(asctime)s %(name)s %(levelname)s %(message)s %(thread)s %(threadName)s"

logging.config.dictConfig(
    {
        "disable_existing_loggers": False,
        "formatters": {
            "json_formatter": {
                "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": _LOG_FORMAT,
            }
        },
        "handlers": {
            "rot_file_handler": {
                "backupCount": 9,
                "class": "logging.handlers.RotatingFileHandler",
                "filename": _LOG_FILE,
                "formatter": "json_formatter",
                "maxBytes": 1_000_000,
            }
        },
        "root": {"handlers": ["rot_file_handler"], "level": "DEBUG"},
        "version": 1,
    }
)
