"""Graphical user interface for pisco."""

from __future__ import annotations

import logging
import queue
import signal
import tkinter as tk
from typing import TYPE_CHECKING, Final

from pisco.input_output import http_image

if TYPE_CHECKING:
    import soco.events_base
    from pisco.input_output import backlight, sonos_device

logger = logging.getLogger(__name__)


class PlaybackInformationLabel(tk.Label):
    """Label that displays the album art of the currently playing track.

    The album art is automatically updated whenever a new track starts playing.
    """

    _av_transport_event_queue: Final[queue.Queue[soco.events_base.Event]]
    _backlight: Final[backlight.AbstractBacklight]
    _max_width: Final[int]
    _max_height: Final[int]
    _refresh_interval_in_ms: Final[int]

    def __init__(  # noqa: PLR0913
        self,
        av_transport_event_queue: queue.Queue[soco.events_base.Event],
        background: str,
        backlight_: backlight.AbstractBacklight,
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
            backlight_: Context manager for activating and deactivating a backlight.
            master: Tk master widget of the label.
            max_width: Maximum width of the album art.
            max_height: Maximum height of the album art.
            refresh_interval_in_ms:
                Time in milliseconds after which the album art is updated
                according to `av_transport_event_queue`.
        """
        super().__init__(background=background, master=master)
        self._av_transport_event_queue = av_transport_event_queue
        self._backlight = backlight_
        self._max_width = max_width
        self._max_height = max_height
        self._refresh_interval_in_ms = refresh_interval_in_ms
        self.after(self._refresh_interval_in_ms, self._process_av_transport_event_queue)

    def _process_av_transport_event(self, event: soco.events_base.Event) -> None:
        adapter = logging.LoggerAdapter(logger, extra={"event": vars(event)})
        adapter.info("Processing AV transport event ...")
        if event.variables["transport_state"] in ("PLAYING", "TRANSITIONING"):
            self._process_track_meta_data(event)
            self._backlight.activate()
        else:
            self._backlight.deactivate()
            self._update_album_art(None)
        adapter.info("AV transport event processed.")

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
        adapter = logging.LoggerAdapter(
            logger, extra={"track_meta_data": vars(track_meta_data)}
        )
        adapter.info("Processing track meta data ...")
        if hasattr(track_meta_data, "album_art_uri"):
            album_art_full_uri = (
                event.service.soco.music_library.build_album_art_full_uri(
                    track_meta_data.album_art_uri
                )
            )
            self._update_album_art(album_art_full_uri)
        adapter.info("Track meta data processed.")

    def _update_album_art(self, absolute_uri: str | None) -> None:
        adapter = logging.LoggerAdapter(logger, extra={"URI": absolute_uri})
        adapter.info("Updating album art ...")
        if absolute_uri is None:
            self.config(image="")  # Empty string means no image.
        else:
            image = http_image.get_photo_image(
                absolute_uri, self._max_width, self._max_height
            )
            self.config(image=image)
        adapter.info("Album art updated.")


class TopLevelWidget(tk.Tk):
    """Pisco's toplevel widget.

    Represents pisco's main window.
    Handles keypress events and signals.
    """

    _sonos_device: Final[sonos_device.SonosDevice]

    def __init__(
        self,
        sonos_device_: sonos_device.SonosDevice,
        window_width: int,
        window_height: int,
    ) -> None:
        """Initializes the graphical user interface and keypress and signal handlers.

        Args:
            sonos_device_: Context manager for the Sonos device to be controlled.
            window_width: Width of the graphical user interface.
            window_height: Height of the graphical user interface.
        """
        super().__init__()
        self._sonos_device = sonos_device_
        self.geometry(f"{window_width}x{window_height}")
        self.title("Pisco")
        self.bind_all("<KeyPress>", self._handle_key_press_event)
        signal.signal(signal.SIGINT, self._handle_int_or_term_signal)
        signal.signal(signal.SIGTERM, self._handle_int_or_term_signal)

    def _handle_int_or_term_signal(self, signal_number: int, _: object) -> None:
        adapter = logging.LoggerAdapter(logger, extra={"signal_number": signal_number})
        adapter.info("Handling signal ...")
        self.destroy()
        adapter.info("Signal handled.")

    def _handle_key_press_event(self, event: tk.Event[tk.Misc]) -> None:
        adapter = logging.LoggerAdapter(logger, extra={"key_press_event": event})
        adapter.info("Handling key press event ...")
        key_symbol = event.keysym
        device = self._sonos_device
        if key_symbol.isdigit():
            device.play_sonos_favorite_by_index(int(key_symbol))
        elif key_symbol in ("Left", "XF86AudioRewind"):
            device.controller.previous()
        elif key_symbol in ("Right", "XF86AudioForward"):
            device.controller.next()
        elif key_symbol in ("Return", "XF86AudioPlay"):
            device.toggle_current_transport_state()
        elif key_symbol == "XF86AudioStop":  # not supported by Rii MX6
            device.controller.stop()
        elif key_symbol == "XF86AudioMute":
            device.controller.mute = not device.controller.mute
        elif key_symbol in ("Up", "XF86AudioRaiseVolume"):
            device.controller.set_relative_volume(+5)
        elif key_symbol in ("Down", "XF86AudioLowerVolume"):
            device.controller.set_relative_volume(-5)
        else:
            adapter.info("No action defined for key press.")
        adapter.info("Key press event handled.")


def run(
    sonos_device_: sonos_device.SonosDevice,
    backlight_: backlight.AbstractBacklight,
    window_width: int,
    window_height: int,
    playback_information_refresh_interval_in_ms: int,
) -> None:
    """Builds the graphical user interface and runs its main loop.

    Args:
        sonos_device_: Context manager for the Sonos device to be controlled.
        backlight_: Context manager for activating and deactivating a backlight.
        window_width: Width of the graphical user interface.
        window_height: Height of the graphical user interface.
        playback_information_refresh_interval_in_ms:
            Time in milliseconds after which the playback information is updated
            according to playback information from `sonos_device_`.
    """
    logger.info("Running pisco user interface ...")
    top_level_widget = TopLevelWidget(sonos_device_, window_width, window_height)
    playback_information_label = PlaybackInformationLabel(
        master=top_level_widget,
        background="black",
        av_transport_event_queue=sonos_device_.av_transport_subscription.events,
        backlight_=backlight_,
        max_width=window_width,
        max_height=window_height,
        refresh_interval_in_ms=playback_information_refresh_interval_in_ms,
    )
    playback_information_label.pack(expand=True, fill="both")
    top_level_widget.mainloop()
    logger.info("Pisco user interface run.")
