from _typeshed import Incomplete

class DidlObject(metaclass=type):
    resources: list[DidlResource]
    def __init__(  # noqa: PLR0913
        self,
        title: str,
        parent_id: str,
        item_id: str,
        restricted: bool = ...,  # noqa: FBT001
        resources: list[DidlResource] | None = ...,
        desc: str = ...,
        **kwargs: Incomplete,
    ) -> None: ...

class DidlResource:
    uri: str
    def __init__(  # noqa: PLR0913
        self,
        uri: str,
        protocol_info: str,
        import_uri: str | None = ...,
        size: int | None = ...,
        duration: str | None = ...,
        bitrate: int | None = ...,
        sample_frequency: int | None = ...,
        bits_per_sample: int | None = ...,
        nr_audio_channels: int | None = ...,
        resolution: str | None = ...,
        color_depth: int | None = ...,
        protection: str | None = ...,
    ) -> None: ...

class ListOfMusicInfoItems(list[object]):
    def __init__(
        self,
        items: list[object],
        number_returned: str,
        total_matches: str,
        update_id: str,
    ) -> None: ...

class SearchResult(ListOfMusicInfoItems):
    def __init__(  # noqa: PLR0913
        self,
        items: list[object],
        search_type: str,
        number_returned: str,
        total_matches: str,
        update_id: str,
    ) -> None: ...
