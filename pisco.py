#! /usr/bin/env python3

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
DEVICE_NAME = "Schlafzimmer"
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
WINDOW_HEIGHT = 320
WINDOW_WIDTH = 240

LOG_DIRECTORY.mkdir(exist_ok=True, parents=True)
logging.config.dictConfig(LOGGING)
logger = logging.getLogger(__name__)


class Backlight:
    def __init__(self, backlight_directory: Path):
        self.backlight_directory = backlight_directory
        self.brightness = backlight_directory / "brightness"
        self.max_brightness = backlight_directory / "max_brightness"

    def activate(self) -> None:
        try:
            max_brightness_value = self.max_brightness.read_text()
            self.brightness.write_text(max_brightness_value)
        except OSError:
            logger.exception(f"Failed to activate backlight {self.backlight_directory}.")

    def deactivate(self) -> None:
        try:
            self.brightness.write_text("0")
        except OSError:
            logger.exception(f"Failed to deactivate backlight {self.backlight_directory}.")


class AlbumArtLabel(tkinter.Label):
    def __init__(self, av_transport_event_queue: queue.Queue, backlight: Backlight, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.av_transport_event_queue = av_transport_event_queue
        self.backlight = backlight
        self.album_art_absolute_uri = ""
        self.album_art_image = self.get_tk_photo_image(self.album_art_absolute_uri)
        self.after(AFTER_MS, self.process_av_transport_event_queue)

    @staticmethod
    def download_resource(uri: str) -> bytes:
        logger.info(f"Downloading resource {uri} ...")
        r = requests.get(uri)
        content = r.content
        logger.info(f"Resource {uri} downloaded.")
        return content

    @classmethod
    def get_tk_photo_image(cls, album_art_absolute_uri: str) -> Optional[PIL.ImageTk.PhotoImage]:
        if album_art_absolute_uri == "":
            return None
        content = cls.download_resource(album_art_absolute_uri)
        image: PIL.Image.Image = PIL.Image.open(io.BytesIO(content))
        image_wo_alpha = cls.remove_alpha_channel(image)
        resized_image = cls.resize_image(image_wo_alpha, WINDOW_WIDTH, WINDOW_HEIGHT)
        tk_photo_image = PIL.ImageTk.PhotoImage(resized_image)
        return tk_photo_image

    def process_av_transport_event(self, event: soco.events_base.Event) -> None:
        logger.info(f"Processing AV transport event {event.__dict__} ...")
        if event.variables["transport_state"] in ("PLAYING", "TRANSITIONING"):
            self.process_track_meta_data(event)
            self.backlight.activate()
        else:
            self.backlight.deactivate()
            self.update_album_art("")
        logger.info("AV transport event processed.")

    def process_av_transport_event_queue(self) -> None:
        try:
            event = self.av_transport_event_queue.get_nowait()
        except queue.Empty:
            pass
        else:
            self.process_av_transport_event(event)
        finally:
            self.after(AFTER_MS, self.process_av_transport_event_queue)

    def process_track_meta_data(self, event: soco.events_base.Event) -> None:
        track_meta_data = event.variables["current_track_meta_data"]
        logger.info(f"Processing track meta data {track_meta_data.__dict__} ...")
        if hasattr(track_meta_data, "album_art_uri"):
            album_art_uri = track_meta_data.album_art_uri
            album_art_absolute_uri = event.service.soco.music_library.build_album_art_full_uri(album_art_uri)
            self.update_album_art(album_art_absolute_uri)
        logger.info("Track meta data processed.")

    @staticmethod
    def remove_alpha_channel(image: PIL.Image.Image) -> PIL.Image.Image:
        logger.info("Removing alpha channel ...")
        if image.mode != "RGBA":
            logger.info("Image does not have an alpha channel.")
            return image
        rgb_image = PIL.Image.new("RGB", image.size, "white")
        rgb_image.paste(image, mask=image.getchannel("A"))
        logger.info("Alpha channel removed.")
        return rgb_image

    @staticmethod
    def resize_image(image: PIL.Image.Image, max_width: int, max_height: int) -> PIL.Image.Image:
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

    def update_album_art(self, album_art_absolute_uri: str) -> None:
        logger.info("Updating album art ...")
        if self.album_art_absolute_uri == album_art_absolute_uri:
            logger.info("Album art is already up-to-date.")
            return
        self.album_art_image = self.get_tk_photo_image(album_art_absolute_uri)
        self.config(image=self.album_art_image)
        self.album_art_absolute_uri = album_art_absolute_uri
        logger.info("Album art updated.")


class App(tkinter.Tk):
    def __init__(self, device: soco.core.SoCo, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device = device
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.title("Pisco")
        self.bind_all("<KeyPress>", self.handle_key_press_event)
        signal.signal(signal.SIGINT, self.handle_int_or_term_signal)
        signal.signal(signal.SIGTERM, self.handle_int_or_term_signal)

    def handle_int_or_term_signal(self, signal_number: int, _) -> None:
        logger.info(f"Received signal {signal_number}.")
        self.destroy()

    def handle_key_press_event(self, event: tkinter.Event) -> None:
        logger.info(f"Handling key press event {event} ...")
        # noinspection PyUnresolvedReferences
        key_symbol: str = event.keysym
        if key_symbol.isdigit():
            self.play_sonos_favorite(int(key_symbol))
        elif key_symbol in ("Left", "XF86AudioRewind"):
            self.device.previous()
        elif key_symbol in ("Right", "XF86AudioForward"):
            self.device.next()
        elif key_symbol in ("Return", "XF86AudioPlay"):
            self.toggle_current_transport_state()
        elif key_symbol == "XF86AudioStop":  # not supported by Rii MX6
            self.device.stop()
        elif key_symbol == "XF86AudioMute":
            self.device.mute = not self.device.mute
        elif key_symbol in ("Up", "XF86AudioRaiseVolume"):
            self.device.set_relative_volume(+5)
        elif key_symbol in ("Down", "XF86AudioLowerVolume"):
            self.device.set_relative_volume(-5)
        else:
            logger.info(f"No action defined for key press {event}.")
        logger.info(f"Key press event {event} handled.")

    def play_sonos_favorite(self, favorite_index: int) -> None:
        logger.info(f"Starting to play Sonos favorite {favorite_index} ...")
        favorite = self.device.music_library.get_sonos_favorites()[favorite_index]
        favorite_uri = favorite.resources[0].uri
        favorite_meta_data = favorite.resource_meta_data
        self.device.play_uri(favorite_uri, favorite_meta_data)
        logger.info(f"Started to play Sonos favorite {favorite_index}.")

    def toggle_current_transport_state(self) -> None:
        logger.info("Toggling current transport state ...")
        transport = self.device.get_current_transport_info()
        state = transport["current_transport_state"]
        if state == "PLAYING":
            self.device.pause()
        else:
            self.device.play()
        logger.info("Toggled current transport state.")


def clean_up(av_transport_subscription: soco.events.Subscription, backlight: Backlight) -> None:
    logger.info("Cleaning up ...")
    av_transport_subscription.unsubscribe()
    av_transport_subscription.event_listener.stop()
    backlight.activate()
    logger.info("Cleaned up.")


def main() -> None:
    device: soco.core.SoCo = soco.discovery.by_name(DEVICE_NAME)
    av_transport_subscription: soco.events.Subscription = device.avTransport.subscribe()
    av_transport_event_queue: queue.Queue = av_transport_subscription.events

    backlight = Backlight(BACKLIGHT_DIRECTORY)

    app = App(device)
    label = AlbumArtLabel(
        master=app,
        background="black",
        av_transport_event_queue=av_transport_event_queue,
        backlight=backlight
    )
    label.pack(expand=True, fill="both")

    try:
        app.mainloop()
    finally:
        clean_up(av_transport_subscription, backlight)


if __name__ == "__main__":
    main()
