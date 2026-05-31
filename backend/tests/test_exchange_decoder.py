"""Tests for app.anomaly.network.exchange — the OrderFilled decoder.

The decoder is a pure function over a JSON-RPC eth_getLogs entry. We
hand-construct logs with known field values and verify the decoded
dict matches.
"""
from __future__ import annotations

from app.anomaly.network.exchange import (
    EXCHANGE_ADDRESSES, ORDER_FILLED_TOPIC, decode_order_filled,
)


def _build_log(
    *, tx_hash: str = "0xaabb",
    order_hash: str = "11" * 32,
    maker: str = "0x" + "a" * 40,
    taker: str = "0x" + "b" * 40,
    maker_asset_id: int = 12345,
    taker_asset_id: int = 67890,
    making: int = 1000,
    taking: int = 990,
    fee: int = 1,
    topic: str = ORDER_FILLED_TOPIC,
) -> dict:
    """Assemble an eth_getLogs entry with the OrderFilled ABI layout."""
    def w(value: str | int) -> str:
        # 32-byte word, hex, zero-padded on the left
        if isinstance(value, int):
            return f"{value:064x}"
        if value.startswith("0x"):
            return value[2:].rjust(64, "0")
        return value.rjust(64, "0")

    data = "0x" + (
        order_hash.ljust(64, "0")  # already 64 hex chars
        + w(maker)
        + w(taker)
        + w(maker_asset_id)
        + w(taker_asset_id)
        + w(making)
        + w(taking)
        + w(fee)
    )
    return {
        "address": EXCHANGE_ADDRESSES[0],
        "topics": [topic],
        "data": data,
        "transactionHash": tx_hash,
    }


def test_decode_order_filled_happy_path():
    log = _build_log()
    out = decode_order_filled(log)
    assert out is not None
    assert out["tx_hash"] == "0xaabb"
    assert out["maker"] == "0x" + "a" * 40
    assert out["taker"] == "0x" + "b" * 40
    assert out["maker_asset_id"] == "12345"
    assert out["taker_asset_id"] == "67890"
    assert out["making"] == 1000
    assert out["taking"] == 990
    assert out["fee"] == 1


def test_decode_returns_none_on_wrong_topic():
    """A log with a different topic[0] is some other event; skip it."""
    log = _build_log(topic="0x" + "f" * 64)
    assert decode_order_filled(log) is None


def test_decode_returns_none_on_short_data():
    """Malformed log (data field shorter than 8 ABI words)."""
    log = _build_log()
    log["data"] = "0x" + "11" * 100  # 200 hex chars, expected 512
    assert decode_order_filled(log) is None


def test_decode_returns_none_on_missing_tx_hash():
    log = _build_log()
    log.pop("transactionHash")
    assert decode_order_filled(log) is None


def test_decode_normalizes_address_case():
    """ABI words may come back checksummed; decoded addresses are lowercase."""
    log = _build_log(maker="0x" + "Ab" * 20, taker="0x" + "CD" * 20)
    out = decode_order_filled(log)
    assert out["maker"] == "0x" + "ab" * 20  # lowercased
    assert out["taker"] == "0x" + "cd" * 20


def test_decode_returns_none_on_non_dict():
    assert decode_order_filled(None) is None
    assert decode_order_filled("not a log") is None
    assert decode_order_filled([]) is None
