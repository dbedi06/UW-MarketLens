"""Per-market trader graph builder.

Nodes are wallet addresses; edges connect wallets that traded in the
same window. The graph is small (one market's worth of trades, possibly
filtered to a window), so we use plain dicts + sets — no `networkx`
dependency. The summary stats below are everything the feature builder
needs.

Counterparty edges are *symmetric* and we deduplicate against a sorted
pair tuple, so a wallet trading with itself or a pair trading 50 times
counts as one edge with a weight. Weights matter — repeat counterparty
patterns are the wash-trade signature.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Trade:
    """Minimal trade record the graph builder consumes. Decoupled from
    the raw RPC log shape so we can swap data sources (Polygon, S1,
    synthetic) without touching the graph code."""
    timestamp: int
    market_id: str
    maker: str
    taker: str
    size: float


@dataclass
class TraderGraph:
    """Output of `build_trader_graph`. Both `wallets` and `edge_weights`
    are kept so feature code can compute additional ad-hoc stats without
    re-walking the trades."""
    wallets: set[str]
    edge_weights: dict[tuple[str, str], int]  # sorted-pair -> count
    trades_per_wallet: dict[str, int]


def _edge_key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


def build_trader_graph(trades: Iterable[Trade]) -> TraderGraph:
    wallets: set[str] = set()
    edge_weights: dict[tuple[str, str], int] = {}
    trades_per_wallet: dict[str, int] = {}
    for t in trades:
        wallets.add(t.maker)
        wallets.add(t.taker)
        trades_per_wallet[t.maker] = trades_per_wallet.get(t.maker, 0) + 1
        trades_per_wallet[t.taker] = trades_per_wallet.get(t.taker, 0) + 1
        if t.maker == t.taker:
            continue  # self-trade — counted in trades_per_wallet but no edge
        key = _edge_key(t.maker, t.taker)
        edge_weights[key] = edge_weights.get(key, 0) + 1
    return TraderGraph(wallets, edge_weights, trades_per_wallet)


# --------------------------------------------------------------------------
# Summary stats — the building blocks the feature builder consumes.
# --------------------------------------------------------------------------

def unique_wallets(g: TraderGraph) -> int:
    return len(g.wallets)


def top_trader_hhi(g: TraderGraph) -> float:
    """Herfindahl-Hirschman concentration of trade counts across
    wallets. Bounded in [0, 1]; 1 means a single wallet did everything,
    near 0 means perfect distribution. Manipulation often concentrates."""
    total = sum(g.trades_per_wallet.values())
    if total == 0:
        return 0.0
    return sum((c / total) ** 2 for c in g.trades_per_wallet.values())


def repeat_counterparty_ratio(g: TraderGraph) -> float:
    """Fraction of edges whose weight is > 1 (the same pair traded with
    each other more than once). High values are a wash-trade smell."""
    if not g.edge_weights:
        return 0.0
    return sum(1 for w in g.edge_weights.values() if w > 1) / len(g.edge_weights)


def largest_component_size(g: TraderGraph) -> int:
    """Size of the biggest weakly-connected component in the graph.
    Linear via plain BFS — no networkx needed."""
    adj: dict[str, set[str]] = {w: set() for w in g.wallets}
    for (a, b) in g.edge_weights:
        adj[a].add(b)
        adj[b].add(a)
    seen: set[str] = set()
    best = 0
    for w in g.wallets:
        if w in seen:
            continue
        # BFS
        frontier = [w]
        seen.add(w)
        comp = 0
        while frontier:
            n = frontier.pop()
            comp += 1
            for m in adj[n]:
                if m not in seen:
                    seen.add(m)
                    frontier.append(m)
        best = max(best, comp)
    return best
