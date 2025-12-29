from __future__ import annotations

from typing import Dict, Iterable, Optional

from playwright.sync_api import TimeoutError, sync_playwright

from scrapers import PriceResult
from scrapers.coins import COINS, CoinConfig
from scrapers.utils import normalize_price_text

HOME_URL = "https://www.coindesk.com/price"
MAX_PAGES = 6


def extract_price_from_row(row) -> Optional[str]:
    cells = row.locator("td")
    if cells.count() > 3:
        candidate = cells.nth(3).inner_text().strip()
        if candidate:
            return candidate

    for i in range(cells.count()):
        candidate = cells.nth(i).inner_text().strip()
        if candidate.startswith("$"):
            return candidate

    return None


def parse_coin_from_row(row) -> Optional[str]:
    cells = row.locator("td")
    if cells.count() > 1:
        name_cell = cells.nth(1).inner_text().strip()
        for line in name_cell.splitlines():
            name = line.strip()
            if name:
                return name
    return None


def fetch_coin_price_from_table(page, coin: CoinConfig) -> Optional[PriceResult]:
    rows = page.locator("table tbody tr")
    if rows.count() == 0:
        raise RuntimeError("Could not find price table on CoinDesk")

    candidates = rows.filter(has_text=coin.name)
    for i in range(candidates.count()):
        row = candidates.nth(i)
        text = extract_price_from_row(row)
        if text:
            return PriceResult(
                slug=coin.slug,
                symbol=coin.symbol,
                name=coin.name,
                source="",
                raw=text,
                price=normalize_price_text(text),
                currency="USD",
                url=HOME_URL,
            )

    return None


def fetch_page_prices(page, coins: Dict[str, CoinConfig]) -> Dict[str, PriceResult]:
    results: Dict[str, PriceResult] = {}
    rows = page.locator("table tbody tr")
    for i in range(rows.count()):
        row = rows.nth(i)
        name = parse_coin_from_row(row)
        if not name:
            continue
        coin = coins.get(name)
        if not coin or coin.slug in results:
            continue
        text = extract_price_from_row(row)
        if not text:
            continue
        results[coin.slug] = PriceResult(
            slug=coin.slug,
            symbol=coin.symbol,
            name=coin.name,
            source="",
            raw=text,
            price=normalize_price_text(text),
            currency="USD",
            url=HOME_URL,
        )
    return results


def fetch_prices(coins: Iterable[CoinConfig]) -> list[PriceResult]:
    results: list[PriceResult] = []
    coin_by_name = {coin.name: coin for coin in coins}
    remaining = {coin.name for coin in coins}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
            )
        )

        for page_number in range(1, MAX_PAGES + 1):
            url = HOME_URL if page_number == 1 else f"{HOME_URL}?page={page_number}"
            page.goto(url, wait_until="domcontentloaded")
            try:
                page.wait_for_selector("table tbody tr", timeout=15000)
            except TimeoutError:
                continue

            page_results = fetch_page_prices(page, coin_by_name)
            for slug, price in page_results.items():
                if price.name in remaining:
                    results.append(price)
                    remaining.discard(price.name)

            if not remaining:
                break

        browser.close()

    return results


class CoinDeskScraper:
    name = "coindesk"

    def __init__(self, coins: Iterable[CoinConfig] = COINS) -> None:
        self._coins = list(coins)

    def fetch(self) -> list[PriceResult]:
        return fetch_prices(self._coins)
