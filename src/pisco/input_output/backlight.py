"""Classes for activating and deactivating sysfs backlights."""


from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    import pathlib
    from types import TracebackType

logger = logging.getLogger(__name__)


class Backlight:
    """Helper for activating and deactivating a sysfs backlight."""

    _directory: pathlib.Path

    def __init__(self, directory: pathlib.Path) -> None:
        """Initializes helper for activating and deactivating a sysfs backlight.

        Args:
            directory: Sysfs directory of the backlight that should be controlled.
        """
        self._directory = directory
        self._assert_backlight_directory()

    def _assert_backlight_directory(self) -> None:
        _assert_directory_existence(self._directory)
        _assert_file_existence(self._brightness)
        _assert_file_existence(self._max_brightness)

    @property
    def _brightness(self) -> pathlib.Path:
        return self._directory / "brightness"

    @property
    def _max_brightness(self) -> pathlib.Path:
        return self._directory / "max_brightness"

    def activate(self) -> None:
        """Sets the brightness to the maximum value."""
        logger.info(
            "Activating backlight ...", extra={"backlight_directory": self._directory}
        )
        try:
            max_brightness_value = self._max_brightness.read_text()
            self._brightness.write_text(max_brightness_value)
        except OSError:
            logger.exception(
                "Could not activate backlight.",
                extra={"backlight_directory": self._directory},
            )
        else:
            logger.info(
                "Backlight activated.", extra={"backlight_directory": self._directory}
            )

    def deactivate(self) -> None:
        """Sets the brightness to zero."""
        logger.info(
            "Deactivating backlight ...", extra={"backlight_directory": self._directory}
        )
        try:
            self._brightness.write_text("0")
        except OSError:
            logger.exception(
                "Could not deactivate backlight.",
                extra={"backlight_directory": self._directory},
            )
        else:
            logger.info(
                "Backlight deactivated.", extra={"backlight_directory": self._directory}
            )


class BacklightManager(contextlib.AbstractContextManager["BacklightManager"]):
    """Context manager for activating and deactivating an optional sysfs backlight."""

    _backlight: Backlight | None

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Activates the backlight if it is present."""
        logger.info(
            "Tearing down manager for optional backlight ...",
            extra={"backlight": self._backlight.__dict__ if self._backlight else None},
        )
        self.activate()
        logger.info(
            "Manager for optional backlight torn down.",
            extra={"backlight": self._backlight.__dict__ if self._backlight else None},
        )

    def __init__(self, directory: pathlib.Path | None) -> None:
        """Initializes helper for (de-)activating a sysfs backlight.

        Args:
            directory:
                Sysfs directory of the backlight to be controlled.
                If `None`, a dummy helper is initialized.
        """
        logger.info(
            "Initializing manager for optional backlight ...",
            extra={"backlight_directory": directory},
        )
        self._backlight = Backlight(directory) if directory else None
        logger.info(
            "Manager for optional backlight initialized.",
            extra={
                "backlight": self._backlight.__dict__ if self._backlight else None,
                "backlight_directory": directory,
            },
        )

    def activate(self) -> None:
        """Sets the brightness to the maximum value if the backlight is present."""
        if self._backlight:
            self._backlight.activate()

    def deactivate(self) -> None:
        """Sets the brightness to zero if the backlight is present."""
        if self._backlight:
            self._backlight.deactivate()


def _assert_directory_existence(path: pathlib.Path) -> None:
    if not path.is_dir():
        raise click.FileError(
            filename=str(path), hint="Does not exist or is not a directory."
        )


def _assert_file_existence(path: pathlib.Path) -> None:
    if not path.is_file():
        raise click.FileError(
            filename=str(path), hint="Does not exist or is not a file."
        )
