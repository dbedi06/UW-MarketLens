"""Polygon on-chain trader-network features for S3.

Wash-trading rings and sybil patterns are invisible to any tabular
detector that doesn't see *who* is trading with *whom*. This subpackage
fetches Polymarket trade events from the Polygon chain, builds a small
trader graph per market, and exposes a handful of graph-summary
features the existing `feature_matrix_streams` pipeline can consume.

Scope caveats (honest):
- USDC funding-chain tracing is intentionally shallow (one or two hops
  upstream of trade-counterparties). Not chain-analysis-firm-grade; we
  document this in the model card so reviewers can calibrate.
- The cache (JSON on disk under `network/cache/`) keeps tests
  offline-safe. Live RPC calls only run when MARKETLENS_POLYGON_LIVE=1
  is set; CI never hits the network.
- We don't claim wallet identification — features are graph-topology
  signals (repeat counterparties, concentration, component sizes), not
  identity attributions.
"""

from .polygon_client import PolygonClient, RpcUnavailable
from .trader_graph import build_trader_graph, TraderGraph
from .network_features import (
    NETWORK_FEATURE_NAMES,
    network_features_for_market,
    nan_network_features,
)
from .exchange import (
    CTF_EXCHANGE_ADDRESS,
    NEGRISK_EXCHANGE_ADDRESS,
    EXCHANGE_ADDRESSES,
    ORDER_FILLED_TOPIC,
    decode_order_filled,
)
from .enrichment import enrich_with_takers

__all__ = [
    "PolygonClient",
    "RpcUnavailable",
    "build_trader_graph",
    "TraderGraph",
    "NETWORK_FEATURE_NAMES",
    "network_features_for_market",
    "nan_network_features",
    "CTF_EXCHANGE_ADDRESS",
    "NEGRISK_EXCHANGE_ADDRESS",
    "EXCHANGE_ADDRESSES",
    "ORDER_FILLED_TOPIC",
    "decode_order_filled",
    "enrich_with_takers",
]
