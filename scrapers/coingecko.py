from __future__ import annotations

import re
from typing import Dict, Iterable, Optional

from playwright.sync_api import TimeoutError, sync_playwright

from scrapers import PriceResult
from scrapers.coins import COINS, CoinConfig
from scrapers.utils import currency_from_text, normalize_price_text

HOME_URL = "https://www.coingecko.com/"
PRICE_REGEX = re.compile(r"[$€£][0-9]")


def extract_price_from_row(row) -> Optional[str]:
    cells = row.locator("td")
    if cells.count() > 4:
        candidate = cells.nth(4).inner_text().strip()
        if candidate and PRICE_REGEX.search(candidate):
            return candidate

    for i in range(cells.count()):
        candidate = cells.nth(i).inner_text().strip()
        if candidate and PRICE_REGEX.search(candidate):
            return candidate

    return None


def fetch_coin_price_from_home(page, coin: CoinConfig) -> PriceResult:
    rows = page.locator("table tbody tr")
    if rows.count() == 0:
        raise RuntimeError("Could not find price table on CoinGecko homepage")

    candidates = rows.filter(has_text=coin.name)
    for i in range(candidates.count()):
        row = candidates.nth(i)
        cells = row.locator("td")
        if cells.count() > 2:
            name_cell = cells.nth(2).inner_text()
            if coin.name not in name_cell:
                continue

        text = extract_price_from_row(row)
        if text:
            return PriceResult(
                slug=coin.slug,
                symbol=coin.symbol,
                name=coin.name,
                source="",
                raw=text,
                price=normalize_price_text(text),
                currency=currency_from_text(text, default="USD"),
                url=HOME_URL,
            )

    raise RuntimeError(f"Could not find price for {coin.slug}")


def fetch_prices(coins: Iterable[CoinConfig]) -> list[PriceResult]:
    results: list[PriceResult] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
            )
        )

        page.goto(HOME_URL, wait_until="domcontentloaded")
        try:
            page.wait_for_selector("table tbody tr", timeout=15000)
        except TimeoutError as exc:
            raise RuntimeError("Timed out waiting for CoinGecko table") from exc

        for coin in coins:
            price = fetch_coin_price_from_home(page, coin)
            results.append(price)

        browser.close()

    return results


class CoinGeckoScraper:
    name = "coingecko"

    def __init__(self, coins: Iterable[CoinConfig] = COINS) -> None:
        self._coins = list(coins)

    def fetch(self) -> list[PriceResult]:
        return fetch_prices(self._coins)
