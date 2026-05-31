"""Thin Polygon RPC client for Polymarket trade events.

Design choices:
- Sync `httpx` (already a project dep for Dilshan's S1 ingestion) over
  raw JSON-RPC. No `web3` dependency — keeps the install footprint
  small.
- Aggressive on-disk JSON cache keyed by request shape. Tests run
  entirely offline against committed cached fixtures; live RPC only
  fires when MARKETLENS_POLYGON_LIVE=1 (and a fixture isn't present).
- Graceful degradation: if the RPC is unreachable AND the cache has no
  hit, `fetch_trades` raises `RpcUnavailable` rather than fabricating
  data. Callers (the feature builder) handle this by emitting all-NaN
  network features and a warning.

We deliberately don't decode trade event logs into typed structs here —
the trade-graph builder treats them as plain dicts. Keeps coupling
loose so the schema can evolve when S1 lands its own ingestion.
"""

from __future__ import annotations
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


CACHE_DIR = Path(__file__).parent / "cache"
DEFAULT_RPC_URL = "https://polygon-bor-rpc.publicnode.com"
LIVE_ENV_FLAG = "MARKETLENS_POLYGON_LIVE"
# Optional override for the RPC URL. Free public nodes prune historical
# blocks aggressively (typically anything older than ~128 blocks).
# Markets whose trades fall outside that window won't get on-chain
# enrichment unless you point at an archive node (e.g., Alchemy free
# tier, QuickNode). See ingestion/README.md for setup notes.
RPC_URL_ENV = "MARKETLENS_POLYGON_RPC_URL"
DEFAULT_TIMEOUT_S = 15.0


class RpcUnavailable(RuntimeError):
    """The Polygon RPC could not be reached AND no cached response
    matched the request. Callers should degrade gracefully (emit NaN
    network features + log)."""


def _cache_key(payload: dict) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


@dataclass
class PolygonClient:
    """Minimal Polygon JSON-RPC client with on-disk cache."""
    rpc_url: str = DEFAULT_RPC_URL
    cache_dir: Path = CACHE_DIR
    timeout_s: float = DEFAULT_TIMEOUT_S

    def __post_init__(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # Env override takes precedence so a deploy can point at an
        # archive node without code changes.
        env_url = os.environ.get(RPC_URL_ENV)
        if env_url and self.rpc_url == DEFAULT_RPC_URL:
            self.rpc_url = env_url

    # ---------------------------------------------------------------- raw
    def _rpc(self, method: str, params: list[Any]) -> Any:
        """Single JSON-RPC call with cache-first semantics. Returns the
        decoded `result` field; raises RpcUnavailable on any failure
        without a cache fallback."""
        payload = {"jsonrpc": "2.0", "id": 1, "method": method,
                   "params": params}
        key = _cache_key(payload)
        cached = self.cache_dir / f"{key}.json"

        if cached.exists():
            return json.loads(cached.read_text(encoding="utf-8"))["result"]

        if os.environ.get(LIVE_ENV_FLAG) != "1":
            raise RpcUnavailable(
                f"no cached response for {method} (params hash={key}) "
                f"and {LIVE_ENV_FLAG}!=1; refusing to hit live RPC"
            )

        try:
            with httpx.Client(timeout=self.timeout_s) as cli:
                r = cli.post(self.rpc_url, json=payload)
                r.raise_for_status()
                body = r.json()
        except (httpx.HTTPError, ValueError) as e:
            raise RpcUnavailable(f"polygon RPC unreachable: {e}") from e

        if "error" in body:
            raise RpcUnavailable(f"polygon RPC error: {body['error']}")

        cached.write_text(
            json.dumps({"request": payload, "result": body.get("result")},
                       indent=2),
            encoding="utf-8",
        )
        return body.get("result")

    # ------------------------------------------------------ public surface
    def block_number(self) -> int:
        """Latest block (cached after first call). Useful as a liveness
        probe and as a default upper bound for log ranges."""
        h = self._rpc("eth_blockNumber", [])
        return int(h, 16)

    def get_logs(self, *, address: str | None = None,
                 topics: list[str | None] | None = None,
                 from_block: int | str = "earliest",
                 to_block: int | str = "latest") -> list[dict]:
        """Wrapper around eth_getLogs. Returns raw log dicts; the graph
        builder decodes the topic / data fields it cares about."""
        params = [{
            "fromBlock": from_block if isinstance(from_block, str)
                         else hex(from_block),
            "toBlock": to_block if isinstance(to_block, str)
                       else hex(to_block),
        }]
        if address:
            params[0]["address"] = address
        if topics is not None:
            params[0]["topics"] = topics
        return self._rpc("eth_getLogs", params) or []
