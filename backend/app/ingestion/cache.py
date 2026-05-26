"""On-disk JSON cache for Polymarket ingestion (B4).

Mirrors the A3 polygon network client cache pattern. Default behaviour
is offline-safe so CI never touches Polymarket:

  Cache hit                  -> return cached, no network
  Cache miss + LIVE=1        -> live fetch, write cache, return
  Cache miss + LIVE not set  -> raise IngestionUnavailable (no fabrication)

`MARKETLENS_POLYMARKET_LIVE=1` is the gate; matches the
`MARKETLENS_POLYGON_LIVE` convention in `app/anomaly/network`.
"""

from __future__ import annotations
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

CACHE_DIR = Path(__file__).parent / "cache"
LIVE_ENV_FLAG = "MARKETLENS_POLYMARKET_LIVE"
DEFAULT_TIMEOUT_S = 15.0


class IngestionUnavailable(RuntimeError):
    """Cache miss AND live calls are disabled (env flag unset). Callers
    should surface this to the user (HTTP 503 from the live route)
    rather than try to fabricate data."""


def cache_key(method: str, url: str, params: dict | None) -> str:
    """Deterministic hash over the request shape. Params are normalized
    by sorting keys so order doesn't matter."""
    payload = {
        "method": method.upper(),
        "url": url,
        "params": dict(sorted((params or {}).items())),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _resolve_dir(cache_dir: Path | None) -> Path:
    """Resolve to the current module-level CACHE_DIR if caller passes
    None. We can't use `cache_dir=CACHE_DIR` as a default because that
    binds the path at function-definition time — tests monkeypatch the
    module attribute and need the lookup to happen per-call."""
    return cache_dir if cache_dir is not None else CACHE_DIR


def _cache_path(key: str, cache_dir: Path | None = None) -> Path:
    d = _resolve_dir(cache_dir)
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{key}.json"


def read(key: str, cache_dir: Path | None = None) -> Any | None:
    p = _cache_path(key, cache_dir)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))["response"]
    except (json.JSONDecodeError, KeyError):
        return None


def write(key: str, request: dict, response: Any,
          cache_dir: Path | None = None) -> None:
    p = _cache_path(key, cache_dir)
    p.write_text(json.dumps({
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "request": request,
        "response": response,
    }, indent=2), encoding="utf-8")


def cached_get(
    client: httpx.Client,
    url: str,
    *,
    params: dict | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    cache_dir: Path | None = None,
) -> Any:
    """Cache-first GET. On cache hit, returns cached response without
    touching the network. On miss, only fetches live if the env flag is
    set; otherwise raises IngestionUnavailable.

    Returns the parsed JSON body (list or dict). Raises:
      IngestionUnavailable  cache miss + LIVE not set
      httpx.HTTPError       live call failed
    """
    key = cache_key("GET", url, params)
    cached = read(key, cache_dir)
    if cached is not None:
        return cached

    if os.environ.get(LIVE_ENV_FLAG) != "1":
        raise IngestionUnavailable(
            f"no cache hit for GET {url} (params={params}); "
            f"set {LIVE_ENV_FLAG}=1 to allow a live fetch"
        )

    r = client.get(url, params=params, timeout=timeout_s)
    r.raise_for_status()
    body = r.json()
    write(key, {"method": "GET", "url": url, "params": params}, body, cache_dir)
    return body
