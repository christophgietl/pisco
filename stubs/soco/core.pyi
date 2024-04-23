from typing import Literal, TypedDict

from _typeshed import Incomplete

from .music_library import MusicLibrary
from .services import AVTransport

class _CurrentTransportInfo(TypedDict):
    current_transport_state: Literal[
        "PLAYING", "TRANSITIONING", "PAUSED_PLAYBACK", "STOPPED"
    ]
    current_transport_status: Literal["OK"] | Incomplete
    current_speed: Literal["1"] | Incomplete

class SoCo(metaclass=type):
    avTransport: AVTransport  # noqa: N815
    music_library: MusicLibrary
    def __init__(self, ip_address: str) -> None: ...
    @property
    def player_name(self) -> str: ...
    def set_relative_volume(self, relative_volume: int) -> int: ...
    def play(self, **kwargs: Incomplete) -> None: ...
    def play_uri(  # noqa: PLR0913
        self,
        uri: str = ...,
        meta: str = ...,
        title: str = ...,
        start: bool = ...,  # noqa: FBT001
        force_radio: bool = ...,  # noqa: FBT001
        **kwargs: Incomplete,
    ) -> bool | None: ...
    def pause(self) -> None: ...
    def stop(self) -> None: ...
    def next(self) -> None: ...
    def previous(self) -> None: ...
    @property
    def mute(self) -> bool: ...
    @mute.setter
    def mute(self, mute: bool) -> None: ...
    def get_current_transport_info(self) -> _CurrentTransportInfo: ...