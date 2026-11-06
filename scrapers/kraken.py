from __future__ import annotations

import re
from typing import Dict, Iterable, Optional

from playwright.sync_api import TimeoutError, expect, sync_playwright

from scrapers import PriceResult
from scrapers.coins import COINS, CoinConfig
from scrapers.utils import normalize_price_text

HOME_URL = "https://www.kraken.com/prices"
CURRENCIES = ["EUR", "USD"]
ROWS_SELECTOR = "table tbody tr:visible"
CURRENCY_SYMBOLS = {
    "EUR": "€",
    "USD": "$",
}


def extract_price_from_row(row) -> Optional[str]:
    cells = row.locator("td:visible")
    # The legacy table has a rank column; the new table starts with the name.
    # Read the first monetary cell, never the change, volume, or market cap.
    for i in range(cells.count()):
        candidate = cells.nth(i).inner_text().strip()
        match = re.search(
            r"[€$]\s*\d[\d.,\s]*|\d[\d.,\s]*[€$]", candidate
        )
        if match:
            return match.group().strip()

    return None


def fetch_coin_price_from_table(
    page, coin: CoinConfig, currency: str
) -> Optional[PriceResult]:
    rows = page.locator(ROWS_SELECTOR)
    if rows.count() == 0:
        raise RuntimeError("Could not find price table on Kraken prices page")

    candidates = rows.filter(has_text=coin.name)
    for i in range(candidates.count()):
        row = candidates.nth(i)
        cells = row.locator("td:visible")
        name_index = 1 if cells.first.inner_text().strip().isdigit() else 0
        name_parts = cells.nth(name_index).inner_text().splitlines()
        if coin.name not in [part.strip() for part in name_parts]:
            continue

        text = extract_price_from_row(row)
        if text and CURRENCY_SYMBOLS[currency] in text:
            return PriceResult(
                slug=coin.slug,
                symbol=coin.symbol,
                name=coin.name,
                source="",
                raw=text,
                price=normalize_price_text(text),
                currency=currency,
                url=HOME_URL,
            )

    return None


def set_currency(page, currency: str) -> None:
    button = page.locator(
        "button[data-testid='prices-table-currency-selector-button']:visible"
    )
    if not button.count():
        button = page.get_by_role(
            "button", name=re.compile(r"^(EUR|USD|GBP|CAD|AUD|CHF|JPY)$")
        )
    if not button.count():
        raise RuntimeError("Could not find Kraken currency selector button")

    button.first.click()
    option = page.get_by_role("option", name=currency, exact=True)
    option.first.wait_for(state="visible", timeout=10000)
    option.first.click()
    expect(page.locator(ROWS_SELECTOR).first).to_contain_text(
        CURRENCY_SYMBOLS[currency], timeout=10000
    )


def fetch_prices_for_currency(
    page, coins: Iterable[CoinConfig], currency: str
) -> Dict[str, PriceResult]:
    results: Dict[str, PriceResult] = {}
    coins = list(coins)
    previous = page.locator("button[data-testid='pagination-prev-page']:visible")
    while previous.count() and previous.first.is_enabled():
        first_row = page.locator(ROWS_SELECTOR).first.inner_text()
        previous.first.click()
        expect(page.locator(ROWS_SELECTOR).first).not_to_have_text(first_row)
    set_currency(page, currency)
    while True:
        for coin in coins:
            if coin.slug not in results:
                result = fetch_coin_price_from_table(page, coin, currency)
                if result is not None:
                    results[coin.slug] = result
        if len(results) == len(coins):
            break
        next_page = page.locator("button[data-testid='pagination-next-page']:visible")
        if not next_page.count() or not next_page.first.is_enabled():
            missing = ", ".join(coin.slug for coin in coins if coin.slug not in results)
            raise RuntimeError(f"Could not find Kraken {currency} prices for {missing}")
        first_row = page.locator(ROWS_SELECTOR).first.inner_text()
        next_page.first.click()
        expect(page.locator(ROWS_SELECTOR).first).not_to_have_text(first_row)
    return results


def fetch_prices(coins: Iterable[CoinConfig]) -> list[PriceResult]:
    coins = list(coins)
    results: list[PriceResult] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            locale="en-US",
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        page.goto(HOME_URL, wait_until="domcontentloaded")
        try:
            page.wait_for_selector(ROWS_SELECTOR, timeout=20000)
        except TimeoutError as exc:
            raise RuntimeError(
                f"Timed out waiting for Kraken prices table at {page.url} "
                f"(title: {page.title()!r})"
            ) from exc

        reject = page.get_by_role("button", name="Reject All", exact=True)
        if reject.is_visible():
            reject.click()

        for currency in CURRENCIES:
            currency_results = fetch_prices_for_currency(page, coins, currency)
            results.extend(currency_results.values())

        browser.close()

    return results


class KrakenScraper:
    name = "kraken"

    def __init__(self, coins: Iterable[CoinConfig] = COINS) -> None:
        self._coins = list(coins)

    def fetch(self) -> list[PriceResult]:
        return fetch_prices(self._coins)
