"""Helper for discovering and controlling a Sonos device."""

from __future__ import annotations

import _thread
import contextlib
import dataclasses
import logging
from typing import Final

import soco.core
import soco.data_structures
import soco.discovery
import soco.events
import soco.events_base

logger = logging.getLogger(__name__)


class SonosDevice(contextlib.AbstractContextManager["SonosDevice"]):
    """Helper for discovering and controlling a Sonos device."""

    av_transport_subscription: Final[soco.events.Subscription]
    controller: Final[soco.core.SoCo]

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        """Unsubscribes from the transport subscription and stops the event listener."""
        adapter = logging.LoggerAdapter(
            logger, extra={"sonos_device_name": self.controller.player_name}
        )
        adapter.info("Tearing down manager for Sonos device ...")
        self.av_transport_subscription.unsubscribe()
        self.av_transport_subscription.event_listener.stop()
        adapter.info("Manager for Sonos device torn down.")

    def __init__(self, name: str) -> None:
        """Discovers a device and creates a controller and an AV transport subscription.

        Args:
            name: Name of the Sonos device to be discovered.

        Raises:
            SonosDeviceNotFoundError: Found no device named `name`.
        """
        adapter = logging.LoggerAdapter(logger, extra={"sonos_device_name": name})
        adapter.info("Initializing manager for Sonos device ...")
        self.controller = _discover_controller(name)
        self.av_transport_subscription = self._initialize_av_transport_subscription()
        adapter.info("Manager for Sonos device initialized.")

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

    def _play_sonos_favorite(self, favorite: soco.data_structures.DidlObject) -> None:
        if hasattr(favorite, "resource_meta_data"):
            self.controller.play_uri(
                uri=favorite.resources[0].uri,
                meta=favorite.resource_meta_data,
            )
            return

        logger.warning(
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
        adapter = logging.LoggerAdapter(logger, extra={"sonos_favorite_index": index})
        adapter.info("Starting to play Sonos favorite ...")
        favorite = self.controller.music_library.get_sonos_favorites()[index]
        if not isinstance(favorite, soco.data_structures.DidlObject):
            logger.error(
                "Could not play Sonos favorite.",
                extra={"favorite": favorite.__dict__, "sonos_favorite_index": index},
            )
            return
        self._play_sonos_favorite(favorite)
        adapter.info("Started to play Sonos favorite.")

    def toggle_current_transport_state(self) -> None:
        """Pauses the track if it is playing and plays the track if it is paused.

        Other transport states (e.g. "STOPPED") are treated similar to paused state.
        """
        logger.info("Toggling current transport state ...")
        transport = self.controller.get_current_transport_info()
        if transport["current_transport_state"] == "PLAYING":
            self.controller.pause()
        else:
            self.controller.play()
        logger.info("Toggled current transport state.")


@dataclasses.dataclass(frozen=True, repr=False)
class SonosDeviceNotFoundError(Exception):
    """Raised when no Sonos device with a given name is found.

    Attributes:
        name: Sonos device that could not be found.
    """

    name: str

    def __post_init__(self) -> None:
        """Initializes exception with the name of the Sonos device."""
        super().__init__(f"Could not find Sonos device named {self.name}.")


def _discover_controller(name: str) -> soco.core.SoCo:
    if (controller := soco.discovery.by_name(name)) is None:
        raise SonosDeviceNotFoundError(name=name)
    return controller
