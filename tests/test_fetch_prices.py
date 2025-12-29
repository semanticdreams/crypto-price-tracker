from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from fetch_prices import output_path, serialize_prices
from scrapers import PriceResult, merge_results
from scrapers.utils import normalize_price_text


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
