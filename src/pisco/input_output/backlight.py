"""Classes for activating and deactivating backlights."""


from __future__ import annotations

import abc
import contextlib
import logging
from typing import TYPE_CHECKING, overload

if TYPE_CHECKING:
    import pathlib
    from types import TracebackType

logger = logging.getLogger(__name__)


class AbstractBacklight(contextlib.AbstractContextManager["AbstractBacklight"]):
    """Context manager for activating and deactivating a backlight.

    When exiting the context, the backlight is activated.
    """

    def __exit__(
        self,
        __exc_type: type[BaseException] | None,
        __exc_value: BaseException | None,
        __traceback: TracebackType | None,
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


class BacklightPathError(Exception):
    """Raised when a backlight path is not a file."""

    _path: pathlib.Path

    def __init__(self, path: pathlib.Path) -> None:
        """Initializes backlight path error.

        Args:
            path: Path that is not a file.
        """
        super().__init__(f"Path {path} is not a file.")
        self._path = path

    @property
    def path(self) -> pathlib.Path:
        """Path that is not a file."""
        return self._path


class DummyBacklight(AbstractBacklight):
    """Virtual backlight that does nothing."""

    def activate(self) -> None:
        """Does nothing."""

    def deactivate(self) -> None:
        """Does nothing."""


class SysfsBacklight(AbstractBacklight):
    """Context manager for activating and deactivating a sysfs backlight."""

    _directory: pathlib.Path

    def __init__(self, directory: pathlib.Path) -> None:
        """Initializes context manager for (de-)activating a sysfs backlight.

        Args:
            directory: Sysfs directory of the backlight to be controlled.

        Raises:
            BacklightPathError: When `directory` does not contain the required files.
        """
        self._directory = directory
        _assert_file_existence(self._brightness)
        _assert_file_existence(self._max_brightness)

    @property
    def _brightness(self) -> pathlib.Path:
        return self._directory / "brightness"

    @property
    def _max_brightness(self) -> pathlib.Path:
        return self._directory / "max_brightness"

    def activate(self) -> None:
        """Sets backlight brightness to maximum value."""
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
        """Sets backlight brightness to zero."""
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


def _assert_file_existence(path: pathlib.Path) -> None:
    """Asserts that a path exists and is a file.

    Raises:
        BacklightPathError: When the path does not exist or is not a file.
    """
    if not path.is_file():
        raise BacklightPathError(path)


@overload
def get_backlight(sysfs_directory: None) -> DummyBacklight:
    ...


@overload
def get_backlight(sysfs_directory: pathlib.Path) -> SysfsBacklight:
    ...


def get_backlight(
    sysfs_directory: pathlib.Path | None,
) -> SysfsBacklight | DummyBacklight:
    """Get context manager for (de-)activating a backlight.

    Args:
        sysfs_directory: Sysfs directory of the backlight.

    Returns:
        Context manager for sysfs backlight or dummy backlight.

    Raises:
        BacklightPathError:
            When `sysfs_directory` does not exist or
            does not contain the required files.
    """
    if sysfs_directory is None:
        return DummyBacklight()
    return SysfsBacklight(sysfs_directory)
