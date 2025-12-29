from __future__ import annotations

from typing import Dict, Iterable, List

from playwright.sync_api import sync_playwright

from scrapers import PriceResult
from scrapers.coins import COINS, CoinConfig

STATIC_URL = (
    "https://www.binance.com/bapi/asset/v2/friendly/asset-service/"
    "product/get-product-static?includeEtf=true"
)
DYNAMIC_URL = (
    "https://www.binance.com/bapi/asset/v2/friendly/asset-service/"
    "product/get-product-dynamic?includeEtf=true"
)
HOME_URL = "https://www.binance.com/en/markets/overview"


def fetch_prices(coins: Iterable[CoinConfig]) -> List[PriceResult]:
    results: List[PriceResult] = []
    coins_by_symbol = {coin.symbol: coin for coin in coins}

    with sync_playwright() as playwright:
        request = playwright.request.new_context()

        static_res = request.get(STATIC_URL)
        dynamic_res = request.get(DYNAMIC_URL)
        if not static_res.ok or not dynamic_res.ok:
            raise RuntimeError("Failed to fetch Binance market data")

        static_data = static_res.json().get("data", [])
        dynamic_data = dynamic_res.json().get("data", [])

        dynamic_map = {item.get("s"): item for item in dynamic_data}

        for entry in static_data:
            if entry.get("q") != "USDT":
                continue
            symbol = entry.get("b")
            coin = coins_by_symbol.get(symbol)
            if not coin:
                continue
            pair = entry.get("s")
            dynamic = dynamic_map.get(pair)
            if not dynamic:
                continue
            last_price = dynamic.get("c")
            if not last_price:
                continue
            try:
                price = float(last_price)
            except ValueError:
                continue

            results.append(
                PriceResult(
                    slug=coin.slug,
                    symbol=coin.symbol,
                    name=coin.name,
                    source="",
                    raw=last_price,
                    price=price,
                    currency="USDT",
                    url=HOME_URL,
                )
            )

        request.dispose()

    return results


class BinanceScraper:
    name = "binance"

    def __init__(self, coins: Iterable[CoinConfig] = COINS) -> None:
        self._coins = list(coins)

    def fetch(self) -> List[PriceResult]:
        return fetch_prices(self._coins)
