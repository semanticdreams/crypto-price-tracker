from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from fetch_prices import output_path, serialize_prices
from scrapers import PriceResult, merge_results
from scrapers.coins import CoinConfig
from scrapers.utils import normalize_price_text
from scrapers import yahoo as yahoo_scraper


def test_normalize_price_text_usd_symbol():
    assert normalize_price_text("$42,123.45") == 42123.45


def test_normalize_price_text_commas_only():
    assert normalize_price_text("12,345") == 12345.0


def test_normalize_price_text_euro_style():
    assert normalize_price_text("1.234,56") == 1234.56


def test_output_path_uses_date():
    target = output_path(Path("data"), datetime(2024, 1, 2, tzinfo=timezone.utc))
    assert target.as_posix() == "data/2024-01-02.json"


def test_merge_results_combines_sources():
    merged = merge_results(
        [
            (
                "source_a",
                [
                    PriceResult(
                        "bitcoin", "BTC", "Bitcoin", "", "$1", 1.0, "USD", "a"
                    )
                ],
            ),
            (
                "source_b",
                [
                    PriceResult(
                        "bitcoin", "BTC", "Bitcoin", "", "$2", 2.0, "USD", "b"
                    )
                ],
            ),
        ]
    )
    assert {entry.source for entry in merged} == {"source_a", "source_b"}


def test_serialize_prices_uses_dicts():
    merged = merge_results(
        [
            (
                "source_a",
                [
                    PriceResult(
                        "bitcoin", "BTC", "Bitcoin", "", "$1", 1.0, "USD", "a"
                    )
                ],
            ),
        ]
    )
    serialized = serialize_prices(merged)
    assert serialized[0]["price"] == 1.0
    assert serialized[0]["source"] == "source_a"


class FakeTextNode:
    def __init__(self, text: str):
        self._text = text

    def inner_text(self) -> str:
        return self._text


class FakeListLocator:
    def __init__(self, items):
        self._items = list(items)

    def count(self) -> int:
        return len(self._items)

    def nth(self, index: int):
        return self._items[index]

    @property
    def first(self):
        return self._items[0]


class FakeButton:
    def click(self) -> None:
        return None


class FakeRow:
    def __init__(self, cells: list[str]):
        self._cells = cells

    def locator(self, selector: str):
        assert selector == "td"
        return FakeListLocator([FakeTextNode(cell) for cell in self._cells])


class FakePage:
    def __init__(self, rows_by_url=None, url="https://consent.yahoo.com/v2/collectConsent"):
        self.url = url
        self._rows_by_url = rows_by_url or {}
        self._rows = []
        self.goto_calls: list[str] = []

    def goto(self, url: str, wait_until="domcontentloaded", timeout=None) -> None:
        self.url = url
        self.goto_calls.append(url)
        self._rows = self._rows_by_url.get(url, [])

    def wait_for_timeout(self, timeout_ms: int) -> None:
        return None

    def wait_for_selector(self, selector: str, timeout: int) -> None:
        assert selector == "table tbody tr"
        return None

    def locator(self, selector: str):
        if selector == "button":
            return FakeListLocator([])
        if selector.startswith("button:has-text("):
            return FakeListLocator([])
        if selector == "table tbody tr":
            return FakeListLocator(self._rows)
        raise AssertionError(f"unexpected selector: {selector}")


class FakeBrowser:
    def __init__(self, page: FakePage):
        self._page = page

    def new_page(self, user_agent: str):
        return self._page

    def close(self) -> None:
        return None


class FakeChromium:
    def __init__(self, page: FakePage):
        self._page = page

    def launch(self):
        return FakeBrowser(self._page)


class FakePlaywright:
    def __init__(self, page: FakePage):
        self.chromium = FakeChromium(page)


class FakePlaywrightContext:
    def __init__(self, page: FakePage):
        self._playwright = FakePlaywright(page)

    def __enter__(self):
        return self._playwright

    def __exit__(self, exc_type, exc, tb):
        return False


def test_yahoo_accept_consent_reloads_requested_url():
    page = FakePage()
    target_url = yahoo_scraper.yahoo_url(start=250)

    yahoo_scraper.accept_consent_if_needed(page, target_url)

    assert page.goto_calls == [target_url]
    assert page.url == target_url


def test_yahoo_matches_arbitrum_symbol_variant():
    coin = CoinConfig(slug="arbitrum", name="Arbitrum", symbol="ARB")
    rows = FakeListLocator(
        [FakeRow(["A\nARB11841-USD", "Arbitrum USD", "", "0.11"])]
    )

    result = yahoo_scraper.fetch_coin_price_from_rows(rows, coin, "test-url")

    assert result is not None
    assert result.slug == "arbitrum"
    assert result.price == 0.11
    assert result.url == "test-url"


def test_yahoo_fetch_prices_scans_later_pages(monkeypatch):
    coin = CoinConfig(slug="arbitrum", name="Arbitrum", symbol="ARB")
    first_url = yahoo_scraper.yahoo_url(start=0)
    second_url = yahoo_scraper.yahoo_url(start=yahoo_scraper.PAGE_SIZE)
    first_page_rows = [FakeRow(["X", "Not Arbitrum USD", "", "1.00"]) for _ in range(yahoo_scraper.PAGE_SIZE)]
    second_page_rows = [FakeRow(["A\nARB11841-USD", "Arbitrum USD", "", "0.11"])]
    page = FakePage(rows_by_url={first_url: first_page_rows, second_url: second_page_rows}, url="about:blank")

    monkeypatch.setattr(
        yahoo_scraper,
        "sync_playwright",
        lambda: FakePlaywrightContext(page),
    )

    results = yahoo_scraper.fetch_prices([coin])

    assert [(entry.slug, entry.price, entry.url) for entry in results] == [
        ("arbitrum", 0.11, second_url)
    ]
    assert page.goto_calls == [first_url, second_url]
