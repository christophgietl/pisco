from .core import SoCo
from .events import Subscription

class AVTransport(Service): ...

class Service:
    soco: SoCo
    def __init__(self, soco: SoCo) -> None: ...
    def subscribe(
        self,
        requested_timeout: None = ...,
        auto_renew: bool = ...,
        event_queue: None = ...,
        strict: bool = ...,
    ) -> Subscription: ...
