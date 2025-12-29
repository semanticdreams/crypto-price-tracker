from __future__ import annotations

from typing import Dict, Iterable, Optional

from playwright.sync_api import TimeoutError, sync_playwright

from scrapers import PriceResult
from scrapers.coins import COINS, CoinConfig
from scrapers.utils import normalize_price_text

HOME_URL = "https://www.kraken.com/prices"
CURRENCIES = ["EUR", "USD"]
CURRENCY_SYMBOLS = {
    "EUR": "€",
    "USD": "$",
}


def extract_price_from_row(row) -> Optional[str]:
    cells = row.locator("td")
    if cells.count() > 2:
        candidate = cells.nth(2).inner_text().strip()
        if candidate and any(symbol in candidate for symbol in CURRENCY_SYMBOLS.values()):
            return candidate

    for i in range(cells.count()):
        candidate = cells.nth(i).inner_text().strip()
        if candidate and any(symbol in candidate for symbol in CURRENCY_SYMBOLS.values()):
            return candidate

    return None


def fetch_coin_price_from_table(page, coin: CoinConfig, currency: str) -> PriceResult:
    rows = page.locator("table tbody tr")
    if rows.count() == 0:
        raise RuntimeError("Could not find price table on Kraken prices page")

    candidates = rows.filter(has_text=coin.name)
    for i in range(candidates.count()):
        row = candidates.nth(i)
        cells = row.locator("td")
        if cells.count() > 1:
            name_cell = cells.nth(1).inner_text()
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
                currency=currency,
                url=HOME_URL,
            )

    raise RuntimeError(f"Could not find price for {coin.slug}")


def set_currency(page, currency: str) -> None:
    button = page.locator(
        "button[data-testid='prices-table-currency-selector-button']:visible"
    )
    if not button.count():
        raise RuntimeError("Could not find Kraken currency selector button")

    button.first.click()
    options = page.locator("[role='option']")
    option = options.filter(has_text=currency)
    if not option.count():
        raise RuntimeError(f"Could not find currency option {currency}")

    option.first.click()
    page.wait_for_timeout(1500)


def fetch_prices_for_currency(
    page, coins: Iterable[CoinConfig], currency: str
) -> Dict[str, PriceResult]:
    results: Dict[str, PriceResult] = {}
    set_currency(page, currency)
    for coin in coins:
        results[coin.slug] = fetch_coin_price_from_table(page, coin, currency)
    return results


def fetch_prices(coins: Iterable[CoinConfig]) -> list[PriceResult]:
    results: list[PriceResult] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
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
            page.wait_for_selector("table tbody tr", timeout=20000)
        except TimeoutError as exc:
            raise RuntimeError("Timed out waiting for Kraken prices table") from exc

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
