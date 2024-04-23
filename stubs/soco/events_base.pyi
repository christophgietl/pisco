from queue import Queue
from typing import Callable

from .services import Service

class Event:
    service: Service
    variables: dict[object, object]
    def __init__(  # noqa: PLR0913
        self,
        sid: str,
        seq: str,
        service: Service,
        timestamp: str,
        variables: dict[object, object] | None = ...,
    ) -> None: ...

class EventListenerBase:
    def stop(self) -> None: ...

class SubscriptionBase:
    events: Queue[Event]
    auto_renew_fail: Callable[[Exception], None] | None
    def __init__(
        self, service: Service, event_queue: Queue[Event] | None = ...
    ) -> None: ...
    def send_event(self, event: Event) -> None: ...
