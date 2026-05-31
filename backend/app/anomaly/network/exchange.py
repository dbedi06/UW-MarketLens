"""Polymarket Exchange contract constants + log decoder.

Encapsulates everything we know about Polymarket's on-chain trade
settlement so the rest of the codebase doesn't have to learn Solidity.
The runtime never computes keccak — the topic hashes are pre-computed
constants. The decoder is a pure function over a JSON-RPC `eth_getLogs`
response entry, returning a typed dict our enricher can index.

Contract addresses (Polygon mainnet, chain id 137)
--------------------------------------------------
From `docs.polymarket.com/resources/contracts.md`:

  CTF Exchange         0xE111180000d2663C0091e4f400237545B87B996B
  NegRisk CTF Exchange 0xe2222d279d744050d28e00520010520000310F59

The CTF Exchange covers binary YES/NO markets (most Polymarket
markets). The NegRisk variant handles multi-outcome markets via a
parallel exchange. Both emit the same `OrderFilled` event shape, so
the decoder works for either.

Event signature
---------------
From the contract source at
`github.com/Polymarket/ctf-exchange/src/exchange/mixins/Trading.sol`:

    event OrderFilled(
        bytes32 orderHash,
        address maker,
        address taker,
        uint256 makerAssetId,
        uint256 takerAssetId,
        uint256 making,
        uint256 taking,
        uint256 fee
    )

None of the parameters are `indexed`, so all eight are packed into
the log's `data` field. `topics[0]` contains the keccak256 of the
event signature string (pre-computed below). `eth_getLogs` therefore
filters trades on the OrderFilled topic, and we decode the data field
to recover maker / taker / asset ids.

Topic hash derivation (one-time, hardcoded)
-------------------------------------------
    from Crypto.Hash import keccak
    k = keccak.new(digest_bits=256)
    k.update(b"OrderFilled(bytes32,address,address,uint256,uint256,uint256,uint256,uint256)")
    print("0x" + k.hexdigest())

yields `0xd0a08e8c493f9c94f29311604c9de1b4e8c8d4c06bd0c789af57f2d65bfec0f6`.
"""

from __future__ import annotations
from typing import Any


# ── Constants (Polygon mainnet) ─────────────────────────────────────────────

CTF_EXCHANGE_ADDRESS = "0xE111180000d2663C0091e4f400237545B87B996B"
NEGRISK_EXCHANGE_ADDRESS = "0xe2222d279d744050d28e00520010520000310F59"
EXCHANGE_ADDRESSES = (CTF_EXCHANGE_ADDRESS, NEGRISK_EXCHANGE_ADDRESS)

ORDER_FILLED_TOPIC = (
    "0xd0a08e8c493f9c94f29311604c9de1b4e8c8d4c06bd0c789af57f2d65bfec0f6"
)


# ── Log decoder ─────────────────────────────────────────────────────────────

def _hex_to_int(h: str) -> int:
    """Hex word → integer. Tolerates 0x prefix and arbitrary length."""
    return int(h, 16)


def _addr_from_word(word: str) -> str:
    """A 32-byte ABI word holding an address has the address in the last
    20 bytes (low-order). Strip the leading 12 bytes of zero-padding and
    lower-case the hex. Polymarket's Data API returns lowercase, so we
    normalize here for consistent string equality downstream."""
    # word is "0x" + 64 hex chars; address is last 40 of those 64.
    cleaned = word[2:] if word.startswith("0x") else word
    if len(cleaned) < 40:
        return ""
    return "0x" + cleaned[-40:].lower()


def decode_order_filled(log: dict[str, Any]) -> dict[str, Any] | None:
    """Decode one `eth_getLogs` entry into a dict our enricher can use.

    Returns
    -------
    dict with keys: tx_hash, maker, taker, maker_asset_id, taker_asset_id,
                    making, taking, fee
    OR
    None — if the log doesn't match the OrderFilled ABI (wrong topic,
    malformed data length, missing transactionHash).

    Honest about ambiguity: this is *not* a full ABI decoder. It assumes
    exactly the OrderFilled signature documented in the module header.
    A contract upgrade that changes the signature will cause this
    function to return None for the new logs; the enricher will then
    leave taker_address empty for those trades. We surface that as a
    debug-log match rate so a future operator sees the drift.
    """
    if not isinstance(log, dict):
        return None
    topics = log.get("topics") or []
    if not topics or topics[0].lower() != ORDER_FILLED_TOPIC.lower():
        return None

    tx_hash = str(log.get("transactionHash", "") or "").lower()
    if not tx_hash:
        return None

    data = log.get("data") or "0x"
    raw = data[2:] if data.startswith("0x") else data
    # 8 × 32-byte words = 512 hex chars expected
    if len(raw) < 512:
        return None

    def word(i: int) -> str:
        return "0x" + raw[i * 64 : (i + 1) * 64]

    return {
        "tx_hash":         tx_hash,
        "order_hash":      word(0),
        "maker":           _addr_from_word(word(1)),
        "taker":           _addr_from_word(word(2)),
        "maker_asset_id":  str(_hex_to_int(word(3))),
        "taker_asset_id":  str(_hex_to_int(word(4))),
        "making":          _hex_to_int(word(5)),
        "taking":          _hex_to_int(word(6)),
        "fee":             _hex_to_int(word(7)),
    }
