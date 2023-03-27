import queue

from .core import SoCo
from .events import Subscription
from .events_base import Event

class Service:
    soco: SoCo

    def __init__(self, soco: SoCo) -> None: ...
    def subscribe(
        self,
        requested_timeout: int | None = ...,
        auto_renew: bool = ...,
        event_queue: queue.Queue[Event] | None = ...,
        strict: bool = ...,
    ) -> Subscription: ...

class AVTransport(Service): ...
