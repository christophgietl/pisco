"""Helper for discovering and controlling a Sonos device."""


from __future__ import annotations

import _thread
import contextlib
import logging
from typing import TYPE_CHECKING

import click
import soco.core
import soco.data_structures
import soco.discovery
import soco.events
import soco.events_base

if TYPE_CHECKING:
    import queue
    from types import TracebackType


logger = logging.getLogger(__name__)


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
        logger.info(
            "Tearing down manager for Sonos device ...",
            extra={"sonos_device_name": self.controller.player_name},
        )
        self._av_transport_subscription.unsubscribe()
        self._av_transport_subscription.event_listener.stop()
        logger.info(
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
        logger.info(
            "Initializing manager for Sonos device ...",
            extra={"sonos_device_name": name},
        )
        self.controller = _discover_controller(name)
        self._av_transport_subscription = self._initialize_av_transport_subscription()
        self.av_transport_event_queue = self._av_transport_subscription.events
        logger.info(
            "Manager for Sonos device initialized.",
            extra={"sonos_device_name": name},
        )

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
        logger.info(
            "Starting to play Sonos favorite ...", extra={"sonos_favorite_index": index}
        )
        favorite = self.controller.music_library.get_sonos_favorites()[index]
        if not isinstance(favorite, soco.data_structures.DidlObject):
            logger.error(
                "Could not play Sonos favorite.",
                extra={"favorite": favorite.__dict__, "sonos_favorite_index": index},
            )
            return
        self._play_sonos_favorite(favorite)
        logger.info(
            "Started to play Sonos favorite.", extra={"sonos_favorite_index": index}
        )

    def toggle_current_transport_state(self) -> None:
        """Pauses the track if it is playing and plays the track if it is paused."""
        logger.info("Toggling current transport state ...")
        transport = self.controller.get_current_transport_info()
        if transport["current_transport_state"] == "PLAYING":
            self.controller.pause()
        else:
            self.controller.play()
        logger.info("Toggled current transport state.")


def _discover_controller(name: str) -> soco.core.SoCo:
    controller = soco.discovery.by_name(name)
    if controller is None:
        msg = f"Could not find Sonos device named {name}."
        raise click.ClickException(msg)
    return controller
