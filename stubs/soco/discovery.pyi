from typing_extensions import Never

from .core import SoCo

def discover(
    timeout: int = ...,
    include_invisible: bool = ...,
    interface_addr: str | None = ...,
    household_id: str = ...,
    allow_network_scan: bool = ...,
    **network_scan_kwargs: Never,
) -> set[SoCo]: ...
def by_name(
    name: str, allow_network_scan: bool = ..., **network_scan_kwargs: Never
) -> SoCo | None: ...
