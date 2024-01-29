"""Classes for activating and deactivating backlights."""

from __future__ import annotations

import abc
import contextlib
import dataclasses
import logging
import os
from typing import TYPE_CHECKING, Literal, overload

if TYPE_CHECKING:
    import pathlib

logger = logging.getLogger(__name__)


class AbstractBacklight(contextlib.AbstractContextManager["AbstractBacklight"]):
    """Context manager for activating and deactivating a backlight.

    When exiting the context, the backlight is activated.
    """

    def __exit__(
        self, __exc_type: object, __exc_value: object, __traceback: object
    ) -> None:
        """Activates the backlight."""
        logger.info("Exiting backlight context ...")
        self.activate()
        logger.info("Backlight context exited.")

    @abc.abstractmethod
    def activate(self) -> None:
        """Sets backlight brightness to maximum value."""

    @abc.abstractmethod
    def deactivate(self) -> None:
        """Sets backlight brightness to zero."""


class DummyBacklight(AbstractBacklight):
    """Virtual backlight that does nothing."""

    def activate(self) -> None:
        """Does nothing."""

    def deactivate(self) -> None:
        """Does nothing."""


class SysfsBacklight(AbstractBacklight):
    """Context manager for activating and deactivating a sysfs backlight."""

    _brightness: pathlib.Path
    _max_brightness: pathlib.Path

    def __init__(self, directory: pathlib.Path) -> None:
        """Initializes context manager for (de-)activating a sysfs backlight.

        Args:
            directory: Sysfs directory of the backlight to be controlled.

        Raises:
            SysfsBacklightFileAccessError:
                When the expected sysfs files in `directory` cannot be read or write.
        """
        self._brightness = directory / "brightness"
        if not os.access(self._brightness, os.W_OK):
            raise SysfsBacklightFileAccessError(mode="write", path=self._brightness)
        self._max_brightness = directory / "max_brightness"
        if not os.access(self._max_brightness, os.R_OK):
            raise SysfsBacklightFileAccessError(mode="read", path=self._max_brightness)

    def activate(self) -> None:
        """Sets backlight brightness to maximum value."""
        logger.info("Activating backlight ...", extra={"brightness": self._brightness})
        try:
            max_brightness_value = self._max_brightness.read_text()
            self._brightness.write_text(max_brightness_value)
        except OSError:
            logger.exception(
                "Could not activate backlight.", extra={"brightness": self._brightness}
            )
        else:
            logger.info("Backlight activated.", extra={"brightness": self._brightness})

    def deactivate(self) -> None:
        """Sets backlight brightness to zero."""
        logger.info(
            "Deactivating backlight ...", extra={"brightness": self._brightness}
        )
        try:
            self._brightness.write_text("0")
        except OSError:
            logger.exception(
                "Could not deactivate backlight.",
                extra={"brightness": self._brightness},
            )
        else:
            logger.info(
                "Backlight deactivated.", extra={"brightness": self._brightness}
            )


@dataclasses.dataclass(frozen=True, repr=False)
class SysfsBacklightFileAccessError(Exception):
    """Raised when a sysfs backlight file cannot be accessed.

    Attributes:
        mode: Mode used while accessing the file.
        path: Sysfs file that could not be accessed.
    """

    mode: Literal["read", "write"]
    path: pathlib.Path

    def __post_init__(self) -> None:
        """Initializes exception with access mode and file path."""
        super().__init__(f"Could not {self.mode} file {self.path}.")


@overload
def get_backlight(sysfs_directory: None) -> DummyBacklight: ...


@overload
def get_backlight(sysfs_directory: pathlib.Path) -> SysfsBacklight: ...


def get_backlight(
    sysfs_directory: pathlib.Path | None,
) -> SysfsBacklight | DummyBacklight:
    """Get context manager for (de-)activating a backlight.

    Args:
        sysfs_directory: Sysfs directory of the backlight.

    Returns:
        Context manager for sysfs backlight or dummy backlight.

    Raises:
        SysfsBacklightFileAccessError:
            When the expected sysfs files in `sysfs_directory` cannot be read or write.
    """
    if sysfs_directory is None:
        return DummyBacklight()
    return SysfsBacklight(sysfs_directory)
