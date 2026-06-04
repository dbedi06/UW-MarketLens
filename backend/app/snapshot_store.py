"""Process-local sid→MarketScore cache.

When a score is produced (live or mock), the producing code stores
it here under its snapshot_id. The snapshot and OG routes look up
by sid and return that same MarketScore — so the verdict card and
the social-preview card always render from the same data.

Lives in its own tiny module so composite.py and mock.py can both
write to it without circular imports.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .schemas import MarketScore

_CACHE: dict[str, "MarketScore"] = {}
_MAX = 128


def put(sid: str, score: "MarketScore") -> None:
    if len(_CACHE) >= _MAX:
        # Evict oldest (insertion-order in CPython 3.7+)
        _CACHE.pop(next(iter(_CACHE)), None)
    _CACHE[sid] = score


def get(sid: str) -> "MarketScore | None":
    return _CACHE.get(sid)


def clear() -> None:
    _CACHE.clear()
