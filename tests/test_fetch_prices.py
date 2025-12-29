from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from fetch_prices import normalize_price_text, output_path


def test_normalize_price_text_usd_symbol():
    assert normalize_price_text("$42,123.45") == 42123.45


def test_normalize_price_text_commas_only():
    assert normalize_price_text("12,345") == 12345.0


def test_normalize_price_text_euro_style():
    assert normalize_price_text("1.234,56") == 1234.56


def test_output_path_uses_date():
    target = output_path(Path("data"), datetime(2024, 1, 2, tzinfo=timezone.utc))
    assert target.as_posix() == "data/2024-01-02.json"
