"""Graphical user interface for pisco."""


from __future__ import annotations

import logging
import queue
import signal
import tkinter as tk
from typing import TYPE_CHECKING, Literal

from pisco.input_output import http_image

if TYPE_CHECKING:
    import PIL.ImageTk
    import soco.events_base

    from pisco.input_output import backlight, sonos_device

logger = logging.getLogger(__name__)


class PlaybackInformationLabel(tk.Label):
    """Label that displays the album art of the currently playing track.

    The album art is automatically updated whenever a new track starts playing.
    """

    _av_transport_event_queue: queue.Queue[soco.events_base.Event]
    _backlight_manager: backlight.BacklightManager
    _max_width: int
    _max_height: int
    _refresh_interval_in_ms: int

    def __init__(  # noqa: PLR0913
        self,
        av_transport_event_queue: queue.Queue[soco.events_base.Event],
        background: str,
        backlight_manager: backlight.BacklightManager,
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
        self._max_width = max_width
        self._max_height = max_height
        self._refresh_interval_in_ms = refresh_interval_in_ms
        self.after(self._refresh_interval_in_ms, self._process_av_transport_event_queue)

    def _process_av_transport_event(self, event: soco.events_base.Event) -> None:
        logger.info(
            "Processing AV transport event ...",
            extra={"event": event.__dict__},
        )
        if event.variables["transport_state"] in ("PLAYING", "TRANSITIONING"):
            self._process_track_meta_data(event)
            self._backlight_manager.activate()
        else:
            self._backlight_manager.deactivate()
            self._update_album_art(None)
        logger.info("AV transport event processed.", extra={"event": event.__dict__})

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
        logger.info(
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
        logger.info(
            "Track meta data processed.",
            extra={"track_meta_data": track_meta_data.__dict__},
        )

    def _update_album_art(self, absolute_uri: str | None) -> None:
        logger.info("Updating album art ...", extra={"URI": absolute_uri})
        image: PIL.ImageTk.PhotoImage | Literal[""] = (
            http_image.get_photo_image(absolute_uri, self._max_width, self._max_height)
            if absolute_uri
            else ""  # Empty string means no image.
        )
        self.config(image=image)
        logger.info("Album art updated.", extra={"URI": absolute_uri})


class TopLevelWidget(tk.Tk):
    """Pisco's toplevel widget.

    Represents pisco's main window.
    Handles keypress events and signals.
    """

    _sonos_device_manager: sonos_device.SonosDeviceManager

    def __init__(
        self,
        sonos_device_manager: sonos_device.SonosDeviceManager,
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
        logger.info("Handling signal ...", extra={"signal_number": signal_number})
        self.destroy()
        logger.info("Signal handled.", extra={"signal_number": signal_number})

    def _handle_key_press_event(self, event: tk.Event[tk.Misc]) -> None:
        logger.info("Handling key press event ...", extra={"key_press_event": event})
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
            logger.info(
                "No action defined for key press.",
                extra={"key_press_event": event},
            )
        logger.info("Key press event handled.")


def run(
    sonos_device_manager: sonos_device.SonosDeviceManager,
    backlight_manager: backlight.BacklightManager,
    window_width: int,
    window_height: int,
    playback_information_refresh_interval_in_ms: int,
) -> None:
    """Builds the graphical user interface and runs its main loop.

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
    logger.info("Running pisco user interface ...")
    top_level_widget = TopLevelWidget(sonos_device_manager, window_width, window_height)
    playback_information_label = PlaybackInformationLabel(
        master=top_level_widget,
        background="black",
        av_transport_event_queue=sonos_device_manager.av_transport_subscription.events,
        backlight_manager=backlight_manager,
        max_width=window_width,
        max_height=window_height,
        refresh_interval_in_ms=playback_information_refresh_interval_in_ms,
    )
    playback_information_label.pack(expand=True, fill="both")
    top_level_widget.mainloop()
    logger.info("Pisco user interface run.")