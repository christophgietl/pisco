"""Command line interface for pisco."""

from __future__ import annotations

import logging
import pathlib

import click

from pisco import _application

_logger = logging.getLogger(__name__)


@click.command()
@click.argument("sonos_device_name")
@click.option(
    "-b",
    "--backlight",
    "backlight_directory",
    help="""
        sysfs directory of the backlight that should be deactivated
        when the device is not playing
    """,
    type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path),
)
@click.option(
    "-w",
    "--width",
    "window_width",
    help="width of the Pisco window",
    type=click.IntRange(min=0),
    default=320,
    show_default=True,
)
@click.option(
    "-h",
    "--height",
    "window_height",
    help="height of the Pisco window",
    type=click.IntRange(min=0),
    default=320,
    show_default=True,
)
@click.option(
    "-r",
    "--refresh",
    "playback_information_refresh_interval",
    help="time in milliseconds after which playback information is updated",
    type=click.IntRange(min=1),
    default=40,
    show_default=True,
)
def cli(
    sonos_device_name: str,
    backlight_directory: pathlib.Path | None,
    window_width: int,
    window_height: int,
    playback_information_refresh_interval: int,
) -> None:
    """Control your Sonos device with your keyboard."""
    try:
        _application.run_application(
            sonos_device_name,
            backlight_directory,
            window_width,
            window_height,
            playback_information_refresh_interval,
        )
    except Exception:
        _logger.exception("Exception has not been handled.")
        raise
