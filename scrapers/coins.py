from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CoinConfig:
    slug: str
    name: str
    symbol: str


COINS = [
    CoinConfig(slug="bitcoin", name="Bitcoin", symbol="BTC"),
    CoinConfig(slug="ethereum", name="Ethereum", symbol="ETH"),
    CoinConfig(slug="solana", name="Solana", symbol="SOL"),
    CoinConfig(slug="cardano", name="Cardano", symbol="ADA"),
    CoinConfig(slug="arbitrum", name="Arbitrum", symbol="ARB"),
    CoinConfig(slug="monero", name="Monero", symbol="XMR"),
    CoinConfig(slug="binancecoin", name="BNB", symbol="BNB"),
]
