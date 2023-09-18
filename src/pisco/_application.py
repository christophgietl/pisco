from __future__ import annotations

import _thread
import contextlib
import functools
import io
import logging.config
import queue
import signal
import tkinter as tk
from typing import TYPE_CHECKING, Literal

import click
import PIL.Image
import PIL.ImageTk
import requests
import soco.core
import soco.data_structures
import soco.events
import soco.events_base

if TYPE_CHECKING:
    import pathlib
    from types import TracebackType


_logger = logging.getLogger(__name__)


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
        self._assert_directory_existence(self._directory)
        self._assert_file_existence(self._brightness)
        self._assert_file_existence(self._max_brightness)

    @staticmethod
    def _assert_directory_existence(path: pathlib.Path) -> None:
        if not path.is_dir():
            raise click.FileError(
                filename=str(path), hint="Does not exist or is not a directory."
            )

    @staticmethod
    def _assert_file_existence(path: pathlib.Path) -> None:
        if not path.is_file():
            raise click.FileError(
                filename=str(path), hint="Does not exist or is not a file."
            )

    @property
    def _brightness(self) -> pathlib.Path:
        return self._directory / "brightness"

    @property
    def _max_brightness(self) -> pathlib.Path:
        return self._directory / "max_brightness"

    def activate(self) -> None:
        """Sets the brightness to the maximum value."""
        _logger.info(
            "Activating backlight ...", extra={"backlight_directory": self._directory}
        )
        try:
            max_brightness_value = self._max_brightness.read_text()
            self._brightness.write_text(max_brightness_value)
        except OSError:
            _logger.exception(
                "Could not activate backlight.",
                extra={"backlight_directory": self._directory},
            )
        else:
            _logger.info(
                "Backlight activated.", extra={"backlight_directory": self._directory}
            )

    def deactivate(self) -> None:
        """Sets the brightness to zero."""
        _logger.info(
            "Deactivating backlight ...", extra={"backlight_directory": self._directory}
        )
        try:
            self._brightness.write_text("0")
        except OSError:
            _logger.exception(
                "Could not deactivate backlight.",
                extra={"backlight_directory": self._directory},
            )
        else:
            _logger.info(
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
        _logger.info(
            "Tearing down manager for optional backlight ...",
            extra={"backlight": self._backlight.__dict__ if self._backlight else None},
        )
        self.activate()
        _logger.info(
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
        _logger.info(
            "Initializing manager for optional backlight ...",
            extra={"backlight_directory": directory},
        )
        self._backlight = Backlight(directory) if directory else None
        _logger.info(
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


class HttpPhotoImageManager:
    """Helper for cached downloading of images and scaling them to the desired size."""

    _max_width: int
    _max_height: int

    def __init__(self, max_width: int, max_height: int) -> None:
        """Initializes helper for image handling.

        Args:
            max_width: Maximum width of the images returned by `get_photo_image`.
            max_height: Maximum height of the image returned by `get_photo_image`.
        """
        self._max_width = max_width
        self._max_height = max_height
        self.get_photo_image = functools.lru_cache(maxsize=1)(
            self._get_photo_image_without_caching
        )

    @staticmethod
    def _download_resource(absolute_uri: str) -> bytes:
        _logger.debug("Downloading resource ...", extra={"URI": absolute_uri})
        response = requests.get(absolute_uri, timeout=10)
        _logger.debug("Resource downloaded.", extra={"URI": absolute_uri})
        return response.content

    def _get_photo_image_without_caching(
        self, absolute_uri: str
    ) -> PIL.ImageTk.PhotoImage:
        _logger.debug(
            "Creating Tkinter-compatible photo image ...",
            extra={"URI": absolute_uri},
        )
        content = self._download_resource(absolute_uri)
        image = PIL.Image.open(io.BytesIO(content))
        image_wo_alpha = self._remove_alpha_channel(image)
        resized_image = self._resize_image(image_wo_alpha)
        photo_image = PIL.ImageTk.PhotoImage(resized_image)
        _logger.debug(
            "Tkinter-compatible photo image created.",
            extra={"URI": absolute_uri},
        )
        return photo_image

    @staticmethod
    def _remove_alpha_channel(image: PIL.Image.Image) -> PIL.Image.Image:
        _logger.debug("Removing alpha channel ...")
        if image.mode != "RGBA":
            _logger.debug(
                "Cannot remove alpha channel: Image does not have an alpha channel."
            )
            return image
        rgb_image = PIL.Image.new("RGB", image.size, "white")
        rgb_image.paste(image, mask=image.getchannel("A"))
        _logger.debug("Alpha channel removed.")
        return rgb_image

    def _resize_image(self, image: PIL.Image.Image) -> PIL.Image.Image:
        _logger.debug("Resizing image ...")
        if self._max_width * image.height <= self._max_height * image.width:
            new_width = self._max_width
            new_height = round(image.height * self._max_width / image.width)
        else:
            new_width = round(image.width * self._max_height / image.height)
            new_height = self._max_height
        resized_image = image.resize(size=(new_width, new_height))
        _logger.debug("Image resized.")
        return resized_image


class PlaybackInformationLabel(tk.Label):
    """Label that displays the album art of the currently playing track.

    The album art is automatically updated whenever a new track starts playing.
    """

    _album_art_image_manager: HttpPhotoImageManager
    _av_transport_event_queue: queue.Queue[soco.events_base.Event]
    _backlight_manager: BacklightManager
    _refresh_interval_in_ms: int

    def __init__(  # noqa: PLR0913
        self,
        av_transport_event_queue: queue.Queue[soco.events_base.Event],
        background: str,
        backlight_manager: BacklightManager,
        master: tk.Tk,
        max_width: int,
        max_height: int,
        refresh_interval_in_ms: int,
    ) -> None:
        """Initializes label for displaying album art.

        Args:
            av_transport_event_queue:
                Events used to update the album art on a regular basis.
            background: Background color of the label.
            backlight_manager:
                Manager for activating and deactivating an optional sysfs backlight.
            master: Tk master widget of the label.
            max_width: Maximum width of the album art.
            max_height: Maximum height of the album art.
            refresh_interval_in_ms:
                Time in milliseconds after which the album art is updated
                according to `av_transport_event_queue`.
        """
        super().__init__(background=background, master=master)
        self._av_transport_event_queue = av_transport_event_queue
        self._backlight_manager = backlight_manager
        self._album_art_image_manager = HttpPhotoImageManager(max_width, max_height)
        self._refresh_interval_in_ms = refresh_interval_in_ms
        self.after(self._refresh_interval_in_ms, self._process_av_transport_event_queue)

    def _process_av_transport_event(self, event: soco.events_base.Event) -> None:
        _logger.info(
            "Processing AV transport event ...",
            extra={"event": event.__dict__},
        )
        if event.variables["transport_state"] in ("PLAYING", "TRANSITIONING"):
            self._process_track_meta_data(event)
            self._backlight_manager.activate()
        else:
            self._backlight_manager.deactivate()
            self._update_album_art(None)
        _logger.info("AV transport event processed.", extra={"event": event.__dict__})

    def _process_av_transport_event_queue(self) -> None:
        try:
            event = self._av_transport_event_queue.get_nowait()
        except queue.Empty:
            pass
        else:
            self._process_av_transport_event(event)
        finally:
            self.after(
                self._refresh_interval_in_ms, self._process_av_transport_event_queue
            )

    def _process_track_meta_data(self, event: soco.events_base.Event) -> None:
        track_meta_data = event.variables["current_track_meta_data"]
        _logger.info(
            "Processing track meta data ...",
            extra={"track_meta_data": track_meta_data.__dict__},
        )
        if hasattr(track_meta_data, "album_art_uri"):
            album_art_full_uri = (
                event.service.soco.music_library.build_album_art_full_uri(
                    track_meta_data.album_art_uri
                )
            )
            self._update_album_art(album_art_full_uri)
        _logger.info(
            "Track meta data processed.",
            extra={"track_meta_data": track_meta_data.__dict__},
        )

    def _update_album_art(self, absolute_uri: str | None) -> None:
        _logger.info("Updating album art ...", extra={"URI": absolute_uri})
        image: PIL.ImageTk.PhotoImage | Literal[""] = (
            self._album_art_image_manager.get_photo_image(absolute_uri)
            if absolute_uri
            else ""  # Empty string means no image.
        )
        self.config(image=image)
        _logger.info("Album art updated.", extra={"URI": absolute_uri})


class SonosDeviceManager(contextlib.AbstractContextManager["SonosDeviceManager"]):
    """Helper for discovering and controlling a Sonos device.

    Attributes:
        av_transport_event_queue:
            Events emitted by the discovered Sonos device
            whenever the transport state changes.
        controller: Controller for the discovered Sonos device.
    """

    _av_transport_subscription: soco.events.Subscription
    av_transport_event_queue: queue.Queue[soco.events_base.Event]
    controller: soco.core.SoCo

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Unsubscribes from the AV transport events and stops the event listener."""
        _logger.info(
            "Tearing down manager for Sonos device ...",
            extra={"sonos_device_name": self.controller.player_name},
        )
        self._av_transport_subscription.unsubscribe()
        self._av_transport_subscription.event_listener.stop()
        _logger.info(
            "Manager for Sonos device torn down.",
            extra={"sonos_device_name": self.controller.player_name},
        )

    def __init__(self, name: str) -> None:
        """Discovers a device and creates a controller and a transport event queue.

        Args:
            name: Name of the Sonos device to be discovered.

        Raises:
            click.ClickException: Found no device named `name`.
        """
        _logger.info(
            "Initializing manager for Sonos device ...",
            extra={"sonos_device_name": name},
        )
        self.controller = self._discover_controller(name)
        self._av_transport_subscription = self._initialize_av_transport_subscription()
        self.av_transport_event_queue = self._av_transport_subscription.events
        _logger.info(
            "Manager for Sonos device initialized.",
            extra={"sonos_device_name": name},
        )

    @staticmethod
    def _discover_controller(name: str) -> soco.core.SoCo:
        controller = soco.discovery.by_name(name)
        if controller is None:
            msg = f"Could not find Sonos device named {name}."
            raise click.ClickException(msg)
        return controller

    def _initialize_av_transport_subscription(self) -> soco.events.Subscription:
        def handle_autorenew_failure(_: Exception) -> None:
            _logger.info("Handling autorenew failure ...")
            _logger.info("Raising a KeyboardInterrupt in the main thread ...")
            _thread.interrupt_main()
            _logger.info("KeyboardInterrupt raised in the main thread.")
            _logger.info("Autorenew failure handled.")

        _logger.debug("Initializing AV transport subscription ...")
        subscription = self.controller.avTransport.subscribe(auto_renew=True)
        subscription.auto_renew_fail = handle_autorenew_failure
        _logger.debug("AV transport subscription initialized.")
        return subscription

    def _play_sonos_favorite(self, favorite: soco.data_structures.DidlObject) -> None:
        if hasattr(favorite, "resource_meta_data"):
            self.controller.play_uri(
                uri=favorite.resources[0].uri,
                meta=favorite.resource_meta_data,
            )
            return

        _logger.warning(
            "Favorite does not have attribute resource_meta_data.",
            extra={"favorite": favorite.__dict__},
        )
        self.controller.play_uri(uri=favorite.resources[0].uri)

    def play_sonos_favorite_by_index(self, index: int) -> None:
        """Plays a track or station from Sonos favorites.

        Args:
            index:
                Position of the track or station to be played
                in the list of Sonos favorites.
        """
        _logger.info(
            "Starting to play Sonos favorite ...", extra={"sonos_favorite_index": index}
        )
        favorite = self.controller.music_library.get_sonos_favorites()[index]
        if not isinstance(favorite, soco.data_structures.DidlObject):
            _logger.error(
                "Could not play Sonos favorite.",
                extra={"favorite": favorite.__dict__, "sonos_favorite_index": index},
            )
            return
        self._play_sonos_favorite(favorite)
        _logger.info(
            "Started to play Sonos favorite.", extra={"sonos_favorite_index": index}
        )

    def toggle_current_transport_state(self) -> None:
        """Pauses the track if it is playing and plays the track if it is paused."""
        _logger.info("Toggling current transport state ...")
        transport = self.controller.get_current_transport_info()
        state = transport["current_transport_state"]
        if state == "PLAYING":
            self.controller.pause()
        else:
            self.controller.play()
        _logger.info("Toggled current transport state.")


class UserInterface(tk.Tk):
    """Pisco's graphical user interface.

    Handles keypress events and signals.
    """

    _sonos_device_manager: SonosDeviceManager

    def __init__(
        self,
        sonos_device_manager: SonosDeviceManager,
        window_width: int,
        window_height: int,
    ) -> None:
        """Initializes the graphical user interface and keypress and signal handlers.

        Args:
            sonos_device_manager: Manager for the Sonos device to be controlled.
            window_width: Width of the graphical user interface.
            window_height: Height of the graphical user interface.
        """
        super().__init__()
        self._sonos_device_manager = sonos_device_manager
        self.geometry(f"{window_width}x{window_height}")
        self.title("Pisco")
        self.bind_all("<KeyPress>", self._handle_key_press_event)
        signal.signal(signal.SIGINT, self._handle_int_or_term_signal)
        signal.signal(signal.SIGTERM, self._handle_int_or_term_signal)

    def _handle_int_or_term_signal(self, signal_number: int, _: object) -> None:
        _logger.info("Handling signal ...", extra={"signal_number": signal_number})
        self.destroy()
        _logger.info("Signal handled.", extra={"signal_number": signal_number})

    def _handle_key_press_event(self, event: tk.Event[tk.Misc]) -> None:
        _logger.info("Handling key press event ...", extra={"key_press_event": event})
        key_symbol = event.keysym
        device_manager = self._sonos_device_manager
        if key_symbol.isdigit():
            device_manager.play_sonos_favorite_by_index(int(key_symbol))
        elif key_symbol in ("Left", "XF86AudioRewind"):
            device_manager.controller.previous()
        elif key_symbol in ("Right", "XF86AudioForward"):
            device_manager.controller.next()
        elif key_symbol in ("Return", "XF86AudioPlay"):
            device_manager.toggle_current_transport_state()
        elif key_symbol == "XF86AudioStop":  # not supported by Rii MX6
            device_manager.controller.stop()
        elif key_symbol == "XF86AudioMute":
            device_manager.controller.mute = not device_manager.controller.mute
        elif key_symbol in ("Up", "XF86AudioRaiseVolume"):
            device_manager.controller.set_relative_volume(+5)
        elif key_symbol in ("Down", "XF86AudioLowerVolume"):
            device_manager.controller.set_relative_volume(-5)
        else:
            _logger.info(
                "No action defined for key press.",
                extra={"key_press_event": event},
            )
        _logger.info("Key press event handled.")


def run_application(
    sonos_device_name: str,
    backlight_directory: pathlib.Path | None,
    window_width: int,
    window_height: int,
    playback_information_refresh_interval_in_ms: int,
) -> None:
    """Manages a Sonos device and an optional backlight and runs the user interface.

    Args:
        sonos_device_name: Name of the Sonos device to be controlled.
        backlight_directory: Sysfs directory of the backlight to be controlled.
        window_width: Width of the graphical user interface.
        window_height: Height of the graphical user interface.
        playback_information_refresh_interval_in_ms:
            Time in milliseconds after which the playback information is updated
            according to playback information from `sonos_device_name`.
    """
    with (
        SonosDeviceManager(sonos_device_name) as sonos_device_manager,
        BacklightManager(backlight_directory) as backlight_manager,
    ):
        run_user_interface(
            sonos_device_manager,
            backlight_manager,
            window_width,
            window_height,
            playback_information_refresh_interval_in_ms,
        )


def run_user_interface(
    sonos_device_manager: SonosDeviceManager,
    backlight_manager: BacklightManager,
    window_width: int,
    window_height: int,
    playback_information_refresh_interval_in_ms: int,
) -> None:
    """Builds the user interface and runs its main loop.

    Args:
        sonos_device_manager: Manager for the Sonos device to be controlled.
        backlight_manager:
            Manager for activating and deactivating an optional sysfs backlight.
        window_width: Width of the graphical user interface.
        window_height: Height of the graphical user interface.
        playback_information_refresh_interval_in_ms:
            Time in milliseconds after which the playback information is updated
            according to playback information from `sonos_device_manager`.
    """
    _logger.info("Running pisco user interface ...")
    user_interface = UserInterface(sonos_device_manager, window_width, window_height)
    playback_information_label = PlaybackInformationLabel(
        master=user_interface,
        background="black",
        av_transport_event_queue=sonos_device_manager.av_transport_event_queue,
        backlight_manager=backlight_manager,
        max_width=window_width,
        max_height=window_height,
        refresh_interval_in_ms=playback_information_refresh_interval_in_ms,
    )
    playback_information_label.pack(expand=True, fill="both")
    user_interface.mainloop()
    _logger.info("Pisco user interface run.")
