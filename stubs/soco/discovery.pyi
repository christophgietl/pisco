from _typeshed import Incomplete

from .core import SoCo

def by_name(
    name: str,
    allow_network_scan: bool = ...,  # noqa: FBT001
    **network_scan_kwargs: Incomplete,
) -> SoCo | None: ...
