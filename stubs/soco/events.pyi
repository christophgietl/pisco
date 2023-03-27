from .events_base import EventListenerBase, SubscriptionBase

class EventListener(EventListenerBase): ...

class Subscription(SubscriptionBase):
    event_listener: EventListener

    def unsubscribe(self, strict: bool = ...) -> Subscription: ...
