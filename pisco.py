#! /usr/bin/env python3

import contextlib
import functools
import io
import logging.config
import queue
import signal
import tkinter
from pathlib import Path
from typing import Optional

import PIL.Image
import PIL.ImageTk
import requests
import soco.events
import soco.events_base
import xdg

AFTER_MS = 40
BACKLIGHT_DIRECTORY = Path("/sys/class/backlight/soc:backlight/")
LOG_DIRECTORY = xdg.XDG_DATA_HOME / "pisco" / "logs"
LOGGING = {
    "disable_existing_loggers": False,
    "formatters": {"default_formatter": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"}},
    "handlers": {
        "rot_file_handler": {
            "backupCount": 9,
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIRECTORY / "sonos_display.log",
            "formatter": "default_formatter",
            "maxBytes": 1_000_000
        },
        "stream_handler": {"class": "logging.StreamHandler", "formatter": "default_formatter"}
    },
    "loggers": {__name__: {"level": "DEBUG"}},
    "root": {"handlers": ["rot_file_handler", "stream_handler"], "level": "INFO"},
    "version": 1
}
SONOS_DEVICE_NAME = "Schlafzimmer"
WINDOW_HEIGHT = 320
WINDOW_WIDTH = 240

LOG_DIRECTORY.mkdir(exist_ok=True, parents=True)
logging.config.dictConfig(LOGGING)
logger = logging.getLogger(__name__)


class Backlight(contextlib.AbstractContextManager):
    def __exit__(self, exc_type, exc_value, traceback) -> None:
        logger.info(f"Tearing down interface to backlight {self._backlight_directory} ...")
        self.activate()
        logger.info(f"Interface to backlight {self._backlight_directory} torn down.")

    def __init__(self, backlight_directory: Path) -> None:
        logger.info(f"Initialising interface to backlight {backlight_directory} ...")
        self._backlight_directory = backlight_directory
        self._brightness = backlight_directory / "brightness"
        self._max_brightness = backlight_directory / "max_brightness"
        logger.info(f"Interface to backlight {backlight_directory} initialised.")

    def activate(self) -> None:
        logger.info(f"Activating backlight {self._backlight_directory} ...")
        try:
            max_brightness_value = self._max_brightness.read_text()
            self._brightness.write_text(max_brightness_value)
        except OSError:
            logger.exception(f"Could not activate backlight {self._backlight_directory}.")
        else:
            logger.info(f"Backlight {self._backlight_directory} activated.")

    def deactivate(self) -> None:
        logger.info(f"Deactivating backlight {self._backlight_directory} ...")
        try:
            self._brightness.write_text("0")
        except OSError:
            logger.exception(f"Could not deactivate backlight {self._backlight_directory}.")
        else:
            logger.info(f"Backlight {self._backlight_directory} deactivated.")


class HttpPhotoImageManager:
    @classmethod
    def _create_photo_image(cls, absolute_uri: str) -> PIL.ImageTk.PhotoImage:
        logger.info(f"Creating Tkinter-compatible photo image from URI {absolute_uri} ...")
        content = cls._download_resource(absolute_uri)
        image: PIL.Image.Image = PIL.Image.open(io.BytesIO(content))
        image_wo_alpha = cls._remove_alpha_channel(image)
        resized_image = cls._resize_image(image_wo_alpha, WINDOW_WIDTH, WINDOW_HEIGHT)
        photo_image = PIL.ImageTk.PhotoImage(resized_image)
        logger.info(f"Tkinter-compatible photo image created from URI {absolute_uri}.")
        return photo_image

    @staticmethod
    def _download_resource(absolute_uri: str) -> bytes:
        logger.info(f"Downloading resource {absolute_uri} ...")
        r = requests.get(absolute_uri)
        content = r.content
        logger.info(f"Resource {absolute_uri} downloaded.")
        return content

    @staticmethod
    def _remove_alpha_channel(image: PIL.Image.Image) -> PIL.Image.Image:
        logger.info("Removing alpha channel ...")
        if image.mode != "RGBA":
            logger.info("Cannot remove alpha channel: Image does not have an alpha channel.")
            return image
        rgb_image = PIL.Image.new("RGB", image.size, "white")
        rgb_image.paste(image, mask=image.getchannel("A"))
        logger.info("Alpha channel removed.")
        return rgb_image

    @staticmethod
    def _resize_image(image: PIL.Image.Image, max_width: int, max_height: int) -> PIL.Image.Image:
        logger.info("Resizing image ...")
        if max_width * image.height <= max_height * image.width:
            new_width = max_width
            new_height = round(image.height * max_width / image.width)
        else:
            new_width = round(image.width * max_height / image.height)
            new_height = max_height
        resized_image = image.resize(size=(new_width, new_height))
        logger.info("Image resized.")
        return resized_image

    @classmethod
    @functools.lru_cache(maxsize=1)
    def get_photo_image(cls, absolute_uri: Optional[str]) -> Optional[PIL.ImageTk.PhotoImage]:
        if absolute_uri is not None:
            photo_image = cls._create_photo_image(absolute_uri)
            return photo_image


class PlaybackInformationLabel(tkinter.Label):
    def __init__(self, av_transport_event_queue: queue.Queue, backlight: Backlight, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._av_transport_event_queue = av_transport_event_queue
        self._backlight = backlight
        self._album_art_image_manager = HttpPhotoImageManager()
        self.after(AFTER_MS, self._process_av_transport_event_queue)

    def _process_av_transport_event(self, event: soco.events_base.Event) -> None:
        logger.info(f"Processing AV transport event {event.__dict__} ...")
        if event.variables["transport_state"] in ("PLAYING", "TRANSITIONING"):
            self._process_track_meta_data(event)
            self._backlight.activate()
        else:
            self._backlight.deactivate()
            self._update_album_art(None)
        logger.info("AV transport event processed.")

    def _process_av_transport_event_queue(self) -> None:
        try:
            event = self._av_transport_event_queue.get_nowait()
        except queue.Empty:
            pass
        else:
            self._process_av_transport_event(event)
        finally:
            self.after(AFTER_MS, self._process_av_transport_event_queue)

    def _process_track_meta_data(self, event: soco.events_base.Event) -> None:
        track_meta_data = event.variables["current_track_meta_data"]
        logger.info(f"Processing track meta data {track_meta_data.__dict__} ...")
        if hasattr(track_meta_data, "album_art_uri"):
            album_art_uri = track_meta_data.album_art_uri
            album_art_absolute_uri = event.service.soco.music_library.build_album_art_full_uri(album_art_uri)
            self._update_album_art(album_art_absolute_uri)
        logger.info("Track meta data processed.")

    def _update_album_art(self, absolute_uri: Optional[str]) -> None:
        logger.info("Updating album art ...")
        album_art_photo_image = self._album_art_image_manager.get_photo_image(absolute_uri)
        self.config(image=album_art_photo_image)
        logger.info("Album art updated.")


class SonosDevice(contextlib.AbstractContextManager):
    def __exit__(self, exc_type, exc_value, traceback) -> None:
        logger.info(f"Tearing down interface to Sonos device {self.controller.player_name} ...")
        self._av_transport_subscription.unsubscribe()
        self._av_transport_subscription.event_listener.stop()
        logger.info(f"Interface to Sonos device {self.controller.player_name} torn down.")

    def __init__(self, name: str) -> None:
        logger.info(f"Initialising interface to Sonos device {name} ...")
        self.controller: soco.core.SoCo = soco.discovery.by_name(name)
        self._av_transport_subscription: soco.events.Subscription = self.controller.avTransport.subscribe()
        self.av_transport_event_queue: queue.Queue = self._av_transport_subscription.events
        logger.info(f"Interface to Sonos device {name} initialised.")

    def play_sonos_favorite(self, favorite_index: int) -> None:
        logger.info(f"Starting to play Sonos favorite {favorite_index} ...")
        favorite = self.controller.music_library.get_sonos_favorites()[favorite_index]
        favorite_uri = favorite.resources[0].uri
        favorite_meta_data = favorite.resource_meta_data
        self.controller.play_uri(favorite_uri, favorite_meta_data)
        logger.info(f"Started to play Sonos favorite {favorite_index}.")

    def toggle_current_transport_state(self) -> None:
        logger.info("Toggling current transport state ...")
        transport = self.controller.get_current_transport_info()
        state = transport["current_transport_state"]
        if state == "PLAYING":
            self.controller.pause()
        else:
            self.controller.play()
        logger.info("Toggled current transport state.")


class UserInterface(tkinter.Tk):
    def __init__(self, sonos_device: SonosDevice, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._sonos_device = sonos_device
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.title("Pisco")
        self.bind_all("<KeyPress>", self._handle_key_press_event)
        signal.signal(signal.SIGINT, self._handle_int_or_term_signal)
        signal.signal(signal.SIGTERM, self._handle_int_or_term_signal)

    def _handle_int_or_term_signal(self, signal_number: int, _) -> None:
        logger.info(f"Handling signal {signal_number} ...")
        self.destroy()
        logger.info(f"Signal {signal_number} handled.")

    def _handle_key_press_event(self, event: tkinter.Event) -> None:
        logger.info(f"Handling key press event {event} ...")
        # noinspection PyUnresolvedReferences
        key_symbol: str = event.keysym
        device = self._sonos_device
        if key_symbol.isdigit():
            device.play_sonos_favorite(int(key_symbol))
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
            logger.info(f"No action defined for key press {event}.")
        logger.info(f"Key press event {event} handled.")


def main() -> None:
    with SonosDevice(SONOS_DEVICE_NAME) as sonos_device:
        with Backlight(BACKLIGHT_DIRECTORY) as backlight:
            logger.info("Running pisco user interface ...")
            user_interface = UserInterface(sonos_device)
            playback_information_label = PlaybackInformationLabel(
                master=user_interface,
                background="black",
                av_transport_event_queue=sonos_device.av_transport_event_queue,
                backlight=backlight
            )
            playback_information_label.pack(expand=True, fill="both")
            user_interface.mainloop()
            logger.info("Pisco user interface run.")


if __name__ == "__main__":
    main()
