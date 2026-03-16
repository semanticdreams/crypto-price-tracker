from __future__ import annotations

import re
from typing import Iterable, Optional

from playwright.sync_api import TimeoutError, sync_playwright

from scrapers import PriceResult
from scrapers.coins import COINS, CoinConfig
from scrapers.utils import normalize_price_text

BASE_URL = "https://finance.yahoo.com/markets/crypto/all/"
PAGE_SIZE = 250
# Defensive cap for scan depth. Current tracked coins are liquid large caps, so a
# top-1000 sweep is sufficient while still preventing endless pagination if Yahoo
# changes the table behavior or repeats pages.
MAX_ROWS_TO_SCAN = 1000


def yahoo_url(start: int = 0, count: int = PAGE_SIZE) -> str:
    return f"{BASE_URL}?start={start}&count={count}"


def accept_consent_if_needed(page, target_url: str) -> None:
    if "consent.yahoo.com" not in page.url:
        return

    buttons = page.locator("button")
    for label in [
        "Accept",
        "Accept all",
        "Agree",
        "I agree",
        "Elfogadom",
        "Az osszes elfogadasa",
        "Az összes elfogadása",
    ]:
        candidate = page.locator(f"button:has-text('{label}')")
        if candidate.count():
            candidate.first.click()
            page.wait_for_timeout(3000)
            break

    if "consent.yahoo.com" in page.url and buttons.count():
        buttons.first.click()
        page.wait_for_timeout(3000)

    if "consent.yahoo.com" in page.url:
        page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)


def extract_price_from_row(row) -> Optional[str]:
    cells = row.locator("td")
    if cells.count() > 3:
        candidate = cells.nth(3).inner_text().strip()
        if candidate:
            return candidate

    for i in range(cells.count()):
        candidate = cells.nth(i).inner_text().strip()
        if candidate and any(char.isdigit() for char in candidate):
            return candidate

    return None


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def row_matches_coin(row, coin: CoinConfig) -> bool:
    cells = row.locator("td")
    if cells.count() <= 1:
        return False

    symbol_cell = normalize_whitespace(cells.nth(0).inner_text())
    name_cell = normalize_whitespace(cells.nth(1).inner_text())

    if name_cell == f"{coin.name} USD":
        return True

    if not name_cell.startswith(coin.name):
        return False

    return f"{coin.symbol}-USD" in symbol_cell or f"{coin.symbol} " in symbol_cell or coin.symbol in symbol_cell


def fetch_coin_price_from_rows(rows, coin: CoinConfig, url: str) -> Optional[PriceResult]:
    for i in range(rows.count()):
        row = rows.nth(i)
        if not row_matches_coin(row, coin):
            continue

        text = extract_price_from_row(row)
        if not text:
            continue

        return PriceResult(
            slug=coin.slug,
            symbol=coin.symbol,
            name=coin.name,
            source="",
            raw=text,
            price=normalize_price_text(text),
            currency="USD",
            url=url,
        )

    return None


def wait_for_table(page) -> None:
    try:
        page.wait_for_selector("table tbody tr", timeout=15000)
    except TimeoutError as exc:
        raise RuntimeError("Timed out waiting for Yahoo Finance table") from exc


def fetch_prices(coins: Iterable[CoinConfig]) -> list[PriceResult]:
    pending = {coin.slug: coin for coin in coins}
    results: list[PriceResult] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
            )
        )

        for start in range(0, MAX_ROWS_TO_SCAN, PAGE_SIZE):
            url = yahoo_url(start=start)
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            accept_consent_if_needed(page, url)
            wait_for_table(page)

            rows = page.locator("table tbody tr")
            row_count = rows.count()
            if row_count == 0:
                raise RuntimeError("Could not find price table on Yahoo Finance crypto page")

            for coin in list(pending.values()):
                result = fetch_coin_price_from_rows(rows, coin, url)
                if result is None:
                    continue
                results.append(result)
                pending.pop(coin.slug, None)

            if not pending:
                break

            if row_count < PAGE_SIZE:
                break

        browser.close()

    if pending:
        missing = ", ".join(sorted(pending))
        raise RuntimeError(f"Could not find price(s) for {missing}")

    return results


class YahooScraper:
    name = "yahoo"

    def __init__(self, coins: Iterable[CoinConfig] = COINS) -> None:
        self._coins = list(coins)

    def fetch(self) -> list[PriceResult]:
        return fetch_prices(self._coins)
