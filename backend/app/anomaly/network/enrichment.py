"""On-chain enrichment: backfill `RawTrade.taker_address` from Polygon
OrderFilled events.

The Data API exposes only `proxyWallet` (the trade initiator), which we
map to `maker_address`. The counterparty is invisible to that API. This
module recovers the counterparty by reading OrderFilled events directly
from the Polymarket Exchange contracts via Polygon RPC.

Flow
----
1. For a list of RawTrades fetched via the Data API, compute the time
   span (min/max timestamp).
2. Convert to a Polygon block range (Polygon mainnet block time ≈ 2s).
3. Call `eth_getLogs(address=<exchange>, topics=[OrderFilled])` for
   both the CTF Exchange and the NegRisk variant, covering that range.
4. Decode every matching log; build a `tx_hash → set[wallet]` map.
5. For each RawTrade, find the wallet(s) in its tx_hash that aren't
   the trade's existing `maker_address`. The first such wallet is the
   counterparty; set `taker_address` to it. If no counterparty is
   found (self-fill, log outside our range, contract upgrade), leave
   `taker_address` empty.

Honest about what this does *not* do
------------------------------------
- It does not fabricate takers. Trades without a matching log pass
  through unchanged.
- It does not resolve multi-hop USDC funding chains. The recovered
  counterparty is the direct on-chain counterparty, nothing more.
- It does not decode share-to-USDC amounts. Price + size still come
  from the Data API; we only use the on-chain log to recover the
  identity field.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Iterable

from .exchange import (
    EXCHANGE_ADDRESSES, ORDER_FILLED_TOPIC, decode_order_filled,
)
from .polygon_client import PolygonClient, RpcUnavailable

logger = logging.getLogger(__name__)


# Polygon mainnet block time ≈ 2.0 seconds (PoS). We use 2 for the
# timestamp → block conversion; the block_window_pad below absorbs the
# imprecision.
_POLYGON_BLOCK_TIME_S = 2.0

# Public Polygon RPC nodes cap eth_getLogs at 10_000 blocks per query.
# We chunk the trade window into pieces of this size and stitch results.
_MAX_BLOCKS_PER_QUERY = 9_500  # under cap, with headroom

# Hard upper bound on total chunks per market to keep cold-start latency
# bounded on the free RPC tier. Beyond this we stop fetching and let the
# oldest trades pass through unenriched. 20 chunks × 9500 blocks ×
# 2s/block ≈ 4.4 days of Polygon — covers the active recent window of
# virtually every market without forcing us to grind through months of
# stale history.
_MAX_QUERY_CHUNKS = 20


def _estimate_block_for_timestamp(
    target_ts: int, *, latest_block: int, latest_ts: int,
) -> int:
    """Linear estimate: blocks-ago = (latest_ts - target_ts) / 2.
    Returns a non-negative int. Used to bound `eth_getLogs` queries
    around our trade window."""
    delta_blocks = max(0, int((latest_ts - target_ts) / _POLYGON_BLOCK_TIME_S))
    return max(0, latest_block - delta_blocks)


def enrich_with_takers(
    client: PolygonClient,
    trades: list,  # list[RawTrade], avoided forward-import for circular safety
    yes_token_id: str,
    *,
    block_window_pad: int = 1000,
) -> list:
    """Backfill `taker_address` on each trade using Polygon RPC.

    Returns a new list (input unchanged). The Data API trade objects
    are frozen-ish; we create new instances via `dataclasses.replace`
    so the original list stays canonical.

    On any RPC failure (no LIVE flag + no cache, network error, RPC
    response error), returns the input trades unchanged and logs a
    warning. The caller never sees an exception from this function;
    enrichment is purely additive.
    """
    if not trades:
        return trades

    try:
        # Compute the time window and convert to Polygon block range.
        # min/max here are computed via the trade timestamps, which our
        # Data API parser stores as tz-aware UTC datetimes.
        ts_unix = [int(t.timestamp.timestamp()) for t in trades]
        min_ts, max_ts = min(ts_unix), max(ts_unix)

        latest_block = client.block_number()
        # We need the latest block's timestamp for the linear estimate.
        # eth_getBlockByNumber returns it; one extra RPC call per cache
        # warm-up.
        latest = client._rpc("eth_getBlockByNumber", ["latest", False])
        latest_ts = int(latest.get("timestamp", "0x0"), 16) if latest else 0
        if latest_ts == 0:
            logger.warning("polygon enrichment: couldn't fetch latest block "
                           "timestamp; skipping")
            return trades

        full_from = _estimate_block_for_timestamp(
            min_ts, latest_block=latest_block, latest_ts=latest_ts,
        )
        full_to = _estimate_block_for_timestamp(
            max_ts, latest_block=latest_block, latest_ts=latest_ts,
        )
        full_from = max(0, full_from - block_window_pad)
        full_to = full_to + block_window_pad

        # Chunk the [full_from, full_to] range into pieces under the
        # public RPC's 10k-block cap. Walk most-recent → oldest so we
        # get the freshest enrichment first; stop after _MAX_QUERY_CHUNKS
        # to keep cold-start latency bounded.
        chunks: list[tuple[int, int]] = []
        cur_to = full_to
        while cur_to > full_from and len(chunks) < _MAX_QUERY_CHUNKS:
            cur_from = max(full_from, cur_to - _MAX_BLOCKS_PER_QUERY + 1)
            chunks.append((cur_from, cur_to))
            cur_to = cur_from - 1

        if len(chunks) >= _MAX_QUERY_CHUNKS and cur_to > full_from:
            logger.debug(
                "polygon enrichment: trade window spans %d blocks; "
                "capped enrichment at %d chunks (~%d blocks back from "
                "latest). Older trades will pass through unenriched.",
                full_to - full_from, _MAX_QUERY_CHUNKS,
                _MAX_QUERY_CHUNKS * _MAX_BLOCKS_PER_QUERY,
            )

        # Fetch logs from both Exchange contracts in each chunk. We
        # can't pass a list of addresses to public Polygon RPCs
        # reliably, so it's two queries per chunk and we merge.
        logs: list[dict] = []
        for from_block, to_block in chunks:
            for addr in EXCHANGE_ADDRESSES:
                try:
                    batch = client.get_logs(
                        address=addr,
                        topics=[ORDER_FILLED_TOPIC],
                        from_block=from_block,
                        to_block=to_block,
                    )
                except RpcUnavailable as exc:
                    logger.warning(
                        "polygon enrichment: %s for %s blocks %d..%d; "
                        "partial coverage", exc, addr, from_block, to_block,
                    )
                    continue
                logs.extend(batch)
        # For the legacy-style debug log below, fall back to full range.
        from_block, to_block = full_from, full_to

        if not logs:
            logger.debug("polygon enrichment: 0 matching logs in block "
                         "range [%d, %d]; trades pass through unchanged.",
                         from_block, to_block)
            return trades

        # Build tx_hash → set of (maker, taker) wallets seen in that tx.
        # A tx can contain multiple OrderFilled events (one trade may
        # fill multiple orders); we collect all addresses then subtract
        # the proxyWallet to find counterparties.
        tx_to_wallets: dict[str, set[str]] = {}
        for log in logs:
            d = decode_order_filled(log)
            if not d:
                continue
            wallets = tx_to_wallets.setdefault(d["tx_hash"], set())
            if d["maker"]:
                wallets.add(d["maker"])
            if d["taker"]:
                wallets.add(d["taker"])

        # Backfill takers. For each trade, look up wallets in its tx;
        # the counterparty is any wallet that isn't the trade's
        # existing maker_address (proxyWallet).
        matched = 0
        enriched: list = []
        for t in trades:
            tx_hash = (t.trade_id or "").lower()
            wallets = tx_to_wallets.get(tx_hash)
            if not wallets:
                enriched.append(t)
                continue
            others = wallets - {t.maker_address.lower()}
            if not others:
                # Self-fill or maker_address mismatch; leave as-is.
                enriched.append(t)
                continue
            # Pick deterministically: sorted to make tests stable.
            counterparty = sorted(others)[0]
            enriched.append(replace(t, taker_address=counterparty))
            matched += 1

        if matched:
            logger.debug(
                "polygon enrichment: filled taker for %d/%d trades "
                "(blocks %d..%d, %d logs decoded)",
                matched, len(trades), from_block, to_block, len(logs),
            )
        return enriched

    except RpcUnavailable as exc:
        logger.warning("polygon enrichment unavailable: %s; trades will "
                       "have taker_address=''", exc)
        return trades
    except Exception as exc:  # noqa: BLE001
        logger.exception("polygon enrichment failed: %s; falling back", exc)
        return trades
