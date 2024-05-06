from _typeshed import Incomplete

from .core import SoCo

def by_name(
    name: str,
    allow_network_scan: bool = ...,
    **network_scan_kwargs: Incomplete,
) -> SoCo | None: ...
