import _thread
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
import click
import requests
import soco.events
import soco.events_base
import xdg

log_directory = xdg.XDG_DATA_HOME / "pisco" / "logs"
log_directory.mkdir(exist_ok=True, parents=True)
logging_configuration = {
    "disable_existing_loggers": False,
    "formatters": {
        "json_formatter": {
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(thread)s - %(threadName)s"
        }
    },
    "handlers": {
        "rot_file_handler": {
            "backupCount": 9,
            "class": "logging.handlers.RotatingFileHandler",
            "filename": log_directory / "pisco.jsonl",
            "formatter": "json_formatter",
            "maxBytes": 1_000_000
        }
    },
    "root": {"handlers": ["rot_file_handler"], "level": "DEBUG"},
    "version": 1
}
logging.config.dictConfig(logging_configuration)
logger = logging.getLogger(__name__)


class Backlight(contextlib.AbstractContextManager):
    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self._backlight_directory:
            logger.info(
                "Tearing down interface to backlight ...",
                extra={"backlight_directory": self._backlight_directory}
            )
            self.activate()
            logger.info(
                "Interface to backlight torn down.",
                extra={"backlight_directory": self._backlight_directory}
            )

    def __init__(self, backlight_directory: Optional[str]) -> None:
        self._backlight_directory = None
        if backlight_directory:
            logger.info("Initializing interface to backlight ...", extra={"backlight_directory": backlight_directory})
            self._backlight_directory = Path(backlight_directory)
            self._brightness = self._backlight_directory / "brightness"
            self._max_brightness = self._backlight_directory / "max_brightness"
            logger.info("Interface to backlight initialized.", extra={"backlight_directory": backlight_directory})

    def activate(self) -> None:
        if self._backlight_directory:
            logger.info("Activating backlight ...", extra={"backlight_directory": self._backlight_directory})
            try:
                max_brightness_value = self._max_brightness.read_text()
                self._brightness.write_text(max_brightness_value)
            except OSError:
                logger.exception(
                    "Could not activate backlight.",
                    extra={"backlight_directory": self._backlight_directory}
                )
            else:
                logger.info("Backlight activated.", extra={"backlight_directory": self._backlight_directory})

    def deactivate(self) -> None:
        if self._backlight_directory:
            logger.info("Deactivating backlight ...", extra={"backlight_directory": self._backlight_directory})
            try:
                self._brightness.write_text("0")
            except OSError:
                logger.exception(
                    "Could not deactivate backlight.",
                    extra={"backlight_directory": self._backlight_directory}
                )
            else:
                logger.info("Backlight deactivated.", extra={"backlight_directory": self._backlight_directory})


class HttpPhotoImageManager:
    def __init__(self, max_width: int, max_height: int) -> None:
        self._max_width = max_width
        self._max_height = max_height

    def _create_photo_image(self, absolute_uri: str) -> PIL.ImageTk.PhotoImage:
        logger.debug("Creating Tkinter-compatible photo image ...", extra={"URI": absolute_uri})
        content = self._download_resource(absolute_uri)
        image: PIL.Image.Image = PIL.Image.open(io.BytesIO(content))
        image_wo_alpha = self._remove_alpha_channel(image)
        resized_image = self._resize_image(image_wo_alpha)
        photo_image = PIL.ImageTk.PhotoImage(resized_image)
        logger.debug("Tkinter-compatible photo image created.", extra={"URI": absolute_uri})
        return photo_image

    @staticmethod
    def _download_resource(absolute_uri: str) -> bytes:
        logger.debug("Downloading resource ...", extra={"URI": absolute_uri})
        r = requests.get(absolute_uri)
        content = r.content
        logger.debug("Resource downloaded.", extra={"URI": absolute_uri})
        return content

    @staticmethod
    def _remove_alpha_channel(image: PIL.Image.Image) -> PIL.Image.Image:
        logger.debug("Removing alpha channel ...")
        if image.mode != "RGBA":
            logger.debug("Cannot remove alpha channel: Image does not have an alpha channel.")
            return image
        rgb_image = PIL.Image.new("RGB", image.size, "white")
        rgb_image.paste(image, mask=image.getchannel("A"))
        logger.debug("Alpha channel removed.")
        return rgb_image

    def _resize_image(self, image: PIL.Image.Image) -> PIL.Image.Image:
        logger.debug("Resizing image ...")
        if self._max_width * image.height <= self._max_height * image.width:
            new_width = self._max_width
            new_height = round(image.height * self._max_width / image.width)
        else:
            new_width = round(image.width * self._max_height / image.height)
            new_height = self._max_height
        resized_image = image.resize(size=(new_width, new_height))
        logger.debug("Image resized.")
        return resized_image

    @functools.lru_cache(maxsize=1)
    def get_photo_image(self, absolute_uri: Optional[str]) -> Optional[PIL.ImageTk.PhotoImage]:
        if absolute_uri:
            photo_image = self._create_photo_image(absolute_uri)
            return photo_image


class PlaybackInformationLabel(tkinter.Label):
    def __init__(
            self,
            av_transport_event_queue: queue.Queue,
            backlight: Backlight,
            max_width: int,
            max_height: int,
            refresh_interval: int,
            *args,
            **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self._av_transport_event_queue = av_transport_event_queue
        self._backlight = backlight
        self._album_art_image_manager = HttpPhotoImageManager(max_width, max_height)
        self._refresh_interval = refresh_interval
        self.after(self._refresh_interval, self._process_av_transport_event_queue)

    def _process_av_transport_event(self, event: soco.events_base.Event) -> None:
        logger.info("Processing AV transport event ...", extra={"event": event.__dict__})
        if event.variables["transport_state"] in ("PLAYING", "TRANSITIONING"):
            self._process_track_meta_data(event)
            self._backlight.activate()
        else:
            self._backlight.deactivate()
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
            self.after(self._refresh_interval, self._process_av_transport_event_queue)

    def _process_track_meta_data(self, event: soco.events_base.Event) -> None:
        track_meta_data = event.variables["current_track_meta_data"]
        logger.info("Processing track meta data ...", extra={"track_meta_data": track_meta_data.__dict__})
        if hasattr(track_meta_data, "album_art_uri"):
            album_art_uri = track_meta_data.album_art_uri
            album_art_absolute_uri = event.service.soco.music_library.build_album_art_full_uri(album_art_uri)
            self._update_album_art(album_art_absolute_uri)
        logger.info("Track meta data processed.", extra={"track_meta_data": track_meta_data.__dict__})

    def _update_album_art(self, absolute_uri: Optional[str]) -> None:
        logger.info("Updating album art ...", extra={"URI": absolute_uri})
        album_art_photo_image = self._album_art_image_manager.get_photo_image(absolute_uri)
        self.config(image=album_art_photo_image)
        logger.info("Album art updated.", extra={"URI": absolute_uri})


class SonosDevice(contextlib.AbstractContextManager):
    def __exit__(self, exc_type, exc_value, traceback) -> None:
        logger.info(
            "Tearing down interface to Sonos device ...",
            extra={"sonos_device_name": self.controller.player_name}
        )
        self._av_transport_subscription.unsubscribe()
        self._av_transport_subscription.event_listener.stop()
        logger.info("Interface to Sonos device torn down.", extra={"sonos_device_name": self.controller.player_name})

    def __init__(self, name: str) -> None:
        logger.info("Initializing interface to Sonos device ...", extra={"sonos_device_name": name})
        self.controller: soco.core.SoCo = soco.discovery.by_name(name)
        self._av_transport_subscription: soco.events.Subscription = self._initialize_av_transport_subscription()
        self.av_transport_event_queue: queue.Queue = self._av_transport_subscription.events
        logger.info("Interface to Sonos device initialized.", extra={"sonos_device_name": name})

    def _initialize_av_transport_subscription(self) -> soco.events.Subscription:
        def handle_autorenew_failure(_: Exception) -> None:
            logger.info("Handling autorenew failure ...")
            logger.info("Raising a KeyboardInterrupt in the main thread ...")
            _thread.interrupt_main()
            logger.info("KeyboardInterrupt raised in the main thread.")
            logger.info("Autorenew failure handled.")

        logger.debug("Initializing AV transport subscription ...")
        subscription = self.controller.avTransport.subscribe(auto_renew=True)
        subscription.auto_renew_fail = handle_autorenew_failure
        logger.debug("AV transport subscription initialized.")
        return subscription

    def play_sonos_favorite(self, favorite_index: int) -> None:
        logger.info("Starting to play Sonos favorite ...", extra={"sonos_favorite_index": favorite_index})
        favorite = self.controller.music_library.get_sonos_favorites()[favorite_index]
        favorite_uri = favorite.resources[0].uri
        favorite_meta_data = favorite.resource_meta_data
        self.controller.play_uri(favorite_uri, favorite_meta_data)
        logger.info("Started to play Sonos favorite.", extra={"sonos_favorite_index": favorite_index})

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
    def __init__(self, sonos_device: SonosDevice, window_width: int, window_height: int, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._sonos_device = sonos_device
        self.geometry(f"{window_width}x{window_height}")
        self.title("Pisco")
        self.bind_all("<KeyPress>", self._handle_key_press_event)
        signal.signal(signal.SIGINT, self._handle_int_or_term_signal)
        signal.signal(signal.SIGTERM, self._handle_int_or_term_signal)

    def _handle_int_or_term_signal(self, signal_number: int, _) -> None:
        logger.info("Handling signal ...", extra={"signal_number": signal_number})
        self.destroy()
        logger.info("Signal handled.", extra={"signal_number": signal_number})

    def _handle_key_press_event(self, event: tkinter.Event) -> None:
        logger.info("Handling key press event ...", extra={"key_press_event": event})
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
            logger.info("No action defined for key press.", extra={"key_press_event": event})
        logger.info("Key press event handled.")


@click.command()
@click.argument('sonos_device_name')
@click.option(
    '-b',
    '--backlight',
    'backlight_directory',
    help="sysfs directory of the backlight that should be deactivated when the device is not playing",
    type=click.Path(exists=True, file_okay=False)
)
@click.option(
    '-w',
    '--width',
    'window_width',
    help="width of the Pisco window",
    type=click.IntRange(min=0),
    default=240,
    show_default=True
)
@click.option(
    '-h',
    '--height',
    'window_height',
    help="height of the Pisco window",
    type=click.IntRange(min=0),
    default=320,
    show_default=True
)
@click.option(
    '-r',
    '--refresh',
    'playback_information_refresh_interval',
    help="time in milliseconds after which playback information is updated",
    type=click.IntRange(min=1),
    default=40,
    show_default=True
)
def main(
        sonos_device_name: str,
        backlight_directory: Optional[str],
        window_width: int,
        window_height: int,
        playback_information_refresh_interval: int
) -> None:
    """Control your Sonos device with your keyboard"""
    with SonosDevice(sonos_device_name) as sonos_device:
        with Backlight(backlight_directory) as backlight:
            logger.info("Running pisco user interface ...")
            user_interface = UserInterface(sonos_device, window_width, window_height)
            playback_information_label = PlaybackInformationLabel(
                master=user_interface,
                background="black",
                av_transport_event_queue=sonos_device.av_transport_event_queue,
                backlight=backlight,
                max_width=window_width,
                max_height=window_height,
                refresh_interval=playback_information_refresh_interval
            )
            playback_information_label.pack(expand=True, fill="both")
            user_interface.mainloop()
            logger.info("Pisco user interface run.")


if __name__ == "__main__":
    main()
