#! /usr/bin/env python3

import io
import logging.config
import queue
import tkinter
from typing import Any, Dict

import PIL.Image
import PIL.ImageTk
import requests
import soco.events
import soco.events_base
import xdg

AFTER_MS = 40
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


class AlbumArtLabel(tkinter.Label):
    def __init__(self, av_transport_event_queue: queue.Queue, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.av_transport_event_queue = av_transport_event_queue
        self.album_art_absolute_uri = ""
        self.album_art_image = None
        self.after(AFTER_MS, self.process_event_queue)

    @staticmethod
    def get_content(image_uri: str) -> bytes:
        logger.info(f"Downloading {image_uri} ...")
        r = requests.get(image_uri)
        content = r.content
        logger.info(f"{image_uri} downloaded.")
        return content

    @classmethod
    def get_tk_photo_image(cls, content: bytes) -> PIL.ImageTk.PhotoImage:
        logger.info("Resizing image ...")
        image: PIL.Image.Image = PIL.Image.open(io.BytesIO(content))
        image_wo_alpha = cls.remove_alpha_channel_if_exists(image)
        resized_image = cls.resize_image(image_wo_alpha, WINDOW_WIDTH, WINDOW_HEIGHT)
        tk_photo_image = PIL.ImageTk.PhotoImage(resized_image)
        logger.info("Image resized.")
        return tk_photo_image

    def process_event(self, event: soco.events_base.Event) -> None:
        logger.debug(f"Received event: {event.variables}")
        track_meta_data = event.variables["current_track_meta_data"]
        if hasattr(track_meta_data, "__dict__"):
            logger.debug(f"Received meta data: {track_meta_data.__dict__}")
        if hasattr(track_meta_data, "album_art_uri"):
            album_art_uri = track_meta_data.album_art_uri
            album_art_absolute_uri = event.service.soco.music_library.build_album_art_full_uri(album_art_uri)
            if self.album_art_absolute_uri != album_art_absolute_uri:
                self.update_album_art(album_art_absolute_uri)
        else:
            logger.info(f"Track meta data does not have an attribute album_art_uri: {repr(track_meta_data)}")

    def process_event_queue(self) -> None:
        try:
            event = self.av_transport_event_queue.get_nowait()
        except queue.Empty:
            pass
        else:
            self.process_event(event)
        finally:
            self.after(AFTER_MS, self.process_event_queue)

    @staticmethod
    def remove_alpha_channel_if_exists(image: PIL.Image.Image) -> PIL.Image.Image:
        if image.mode == "RGBA":
            rgb_image = PIL.Image.new("RGB", image.size, "white")
            rgb_image.paste(image, mask=image.getchannel("A"))
            return rgb_image
        return image

    @staticmethod
    def resize_image(image: PIL.Image.Image, max_width: int, max_height: int) -> PIL.Image.Image:
        if max_width * image.height <= max_height * image.width:
            new_width = max_width
            new_height = round(image.height * max_width / image.width)
        else:
            new_width = round(image.width * max_height / image.height)
            new_height = max_height
        resized_image = image.resize(size=(new_width, new_height))
        return resized_image

    def update_album_art(self, album_art_absolute_uri: str) -> None:
        content = self.get_content(album_art_absolute_uri)
        self.album_art_image = self.get_tk_photo_image(content)
        self.config(image=self.album_art_image)
        self.album_art_absolute_uri = album_art_absolute_uri


class App(tkinter.Tk):
    def __init__(self, device: soco.core.SoCo, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device = device
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.title("Pisco")
        self.bind_all("<KeyPress>", self.handle_key_press_event)

    def handle_key_press_event(self, event: tkinter.Event) -> None:
        # noinspection PyUnresolvedReferences
        key: str = event.char
        keysym: str = event.keysym
        if key.isdigit():
            favorite_number = (int(key) - 1) % 10
            favorite = self.device.music_library.get_sonos_favorites()[favorite_number]
            favorite_uri = favorite.resources[0].uri
            favorite_meta_data = favorite.resource_meta_data
            self.device.play_uri(favorite_uri, favorite_meta_data)
        elif keysym == "XF86AudioRewind":
            self.device.previous()
        elif keysym == "XF86AudioForward":
            self.device.next()
        elif keysym == "XF86AudioPlay":
            self.toggle_play_pause()
        elif keysym == "XF86AudioStop":  # not supported by Rii MX6
            self.device.stop()
        elif keysym == "XF86AudioMute":
            self.device.mute = not self.device.mute
        elif keysym == "XF86AudioRaiseVolume":
            self.device.set_relative_volume(+5)
        elif keysym == "XF86AudioLowerVolume":
            self.device.set_relative_volume(-5)
        else:
            logger.info(f"Unknown key pressed: {event}")

    def toggle_play_pause(self) -> None:
        transport: Dict[str, Any] = self.device.get_current_transport_info()
        state = transport["current_transport_state"]
        if state == "PLAYING":
            self.device.pause()
        else:
            self.device.play()


def main() -> None:
    device: soco.core.SoCo = soco.discovery.by_name(DEVICE_NAME)
    av_transport_subscription: soco.events.Subscription = device.avTransport.subscribe()
    av_transport_event_queue: queue.Queue = av_transport_subscription.events

    app = App(device)
    label = AlbumArtLabel(master=app, background="black", av_transport_event_queue=av_transport_event_queue)
    label.pack(expand=True, fill="both")

    try:
        app.mainloop()
    finally:
        av_transport_subscription.unsubscribe()
        av_transport_subscription.event_listener.stop()


if __name__ == "__main__":
    main()
