from _typeshed import Incomplete

from .core import SoCo
from .data_structures import SearchResult

class MusicLibrary:
    def __init__(self, soco: SoCo | None = ...) -> None: ...
    def build_album_art_full_uri(self, url: str) -> str: ...
    def get_sonos_favorites(
        self, *args: Incomplete, **kwargs: Incomplete
    ) -> SearchResult: ...
