from pathlib import Path
import sys

import pytest
from playwright.sync_api import sync_playwright

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scrapers.coins import CoinConfig
from scrapers.kraken import (
    ROWS_SELECTOR,
    fetch_coin_price_from_table,
    fetch_prices_for_currency,
)


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    page = browser.new_page()
    yield page
    page.close()


@pytest.mark.parametrize("rank", ["", "<td>1</td>"])
def test_reads_visible_price_in_both_table_layouts(page, rank):
    page.set_content(f"""
        <table hidden><tbody><tr><td>Bitcoin</td><td>$999</td></tr></tbody></table>
        <table><tbody>
          <tr>{rank}<td>Wrapped Bitcoin<br>WBTC</td><td>$50</td></tr>
          <tr>{rank}<td>BTC<br>Bitcoin<br>BTC</td>
            <td><span>$42,123.45</span><span hidden>$42,123.45</span></td>
            <td>5.32%</td><td>$1.2T</td></tr>
        </tbody></table>
    """)

    page.wait_for_selector(ROWS_SELECTOR, timeout=1000)
    result = fetch_coin_price_from_table(
        page, CoinConfig("bitcoin", "Bitcoin", "BTC"), "USD"
    )

    assert result is not None
    assert result.raw == "$42,123.45"
    assert result.price == 42123.45
    assert fetch_coin_price_from_table(
        page, CoinConfig("bitcoin", "Bitcoin", "BTC"), "EUR"
    ) is None


def test_currency_switch_and_pagination_use_active_table(page):
    page.set_content("""
        <table hidden><tbody><tr><td>Bitcoin</td><td>€999</td></tr></tbody></table>
        <button id="currency" onclick="document.querySelector('#options').hidden=false">EUR</button>
        <div id="options" hidden>
          <div role="option" onclick="setCurrency('EUR')">EUR</div>
          <div role="option" onclick="setCurrency('USD')">USD</div>
        </div>
        <table><tbody id="rows"></tbody></table>
        <button data-testid="pagination-prev-page" onclick="index--; render()">Previous</button>
        <button data-testid="pagination-next-page" onclick="index++; render()">Next</button>
        <script>
          let index = 0, currency = 'EUR';
          function render() {
            const name = index === 0 ? 'Bitcoin' : 'Arbitrum';
            const price = currency === 'EUR' ? '€12.34' : '$23.45';
            document.querySelector('#rows').innerHTML =
              `<tr><td>${name}</td><td>${price}</td><td>5%</td><td>$1.2B</td></tr>`;
            document.querySelector('[data-testid="pagination-prev-page"]').disabled = index === 0;
            document.querySelector('[data-testid="pagination-next-page"]').disabled = index === 1;
          }
          function setCurrency(value) {
            currency = value;
            document.querySelector('#currency').innerText = value;
            document.querySelector('#options').hidden = true;
            setTimeout(render, 50);
          }
          render();
        </script>
    """)
    coins = [
        CoinConfig("bitcoin", "Bitcoin", "BTC"),
        CoinConfig("arbitrum", "Arbitrum", "ARB"),
    ]

    euros = fetch_prices_for_currency(page, iter(coins), "EUR")
    dollars = fetch_prices_for_currency(page, iter(coins), "USD")

    assert {coin: quote.price for coin, quote in euros.items()} == {
        "bitcoin": 12.34, "arbitrum": 12.34,
    }
    assert {coin: quote.price for coin, quote in dollars.items()} == {
        "bitcoin": 23.45, "arbitrum": 23.45,
    }

    with pytest.raises(RuntimeError, match="Could not find Kraken USD prices for missing"):
        fetch_prices_for_currency(page, [CoinConfig("missing", "Missing", "???")], "USD")
