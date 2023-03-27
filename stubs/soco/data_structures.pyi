from typing_extensions import Never

class DidlResource:
    uri: str

    def __init__(
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

class DidlMetaClass(type):
    def __new__(cls, name: Never, bases: Never, attrs: Never) -> type: ...

class DidlObject(metaclass=DidlMetaClass):
    resources: list[DidlResource]

    def __init__(
        self,
        title: str,
        parent_id: str,
        item_id: str,
        restricted: bool = ...,
        resources: list[DidlResource] | None = ...,
        desc: str = ...,
        **kwargs: Never,
    ) -> None: ...

class ListOfMusicInfoItems(list[object]):
    def __init__(
        self,
        items: Never,
        number_returned: Never,
        total_matches: Never,
        update_id: Never,
    ) -> None: ...

class SearchResult(ListOfMusicInfoItems):
    def __init__(
        self,
        items: Never,
        search_type: Never,
        number_returned: Never,
        total_matches: Never,
        update_id: Never,
    ) -> None: ...
