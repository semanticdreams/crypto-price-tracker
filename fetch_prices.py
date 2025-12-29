#!/usr/bin/env python3
import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Optional

from playwright.sync_api import TimeoutError, sync_playwright

HOME_URL = "https://www.coingecko.com/"
PRICE_REGEX = re.compile(r"\$[0-9]")


@dataclass(frozen=True)
class CoinConfig:
    slug: str
    name: str


COINS = [
    CoinConfig(slug="bitcoin", name="Bitcoin"),
    CoinConfig(slug="ethereum", name="Ethereum"),
    CoinConfig(slug="solana", name="Solana"),
    CoinConfig(slug="cardano", name="Cardano"),
    CoinConfig(slug="arbitrum", name="Arbitrum"),
    CoinConfig(slug="monero", name="Monero"),
    CoinConfig(slug="binancecoin", name="BNB"),
]


def normalize_price_text(text: str) -> float:
    cleaned = re.sub(r"[^0-9,\.]", "", text)
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned and "." not in cleaned:
        if re.search(r",\d{1,2}$", cleaned):
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")

    if not cleaned:
        raise ValueError(f"Could not parse price from {text!r}")

    return float(cleaned)


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


def fetch_coin_price_from_home(page, coin: CoinConfig) -> Dict[str, str]:
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
            return {
                "raw": text,
                "usd": normalize_price_text(text),
                "url": HOME_URL,
            }

    raise RuntimeError(f"Could not find price for {coin.slug}")


def fetch_prices(coins: Iterable[CoinConfig]) -> Dict[str, Dict[str, str]]:
    results: Dict[str, Dict[str, str]] = {}
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
            results[coin.slug] = {
                "name": coin.name,
                **fetch_coin_price_from_home(page, coin),
            }

        browser.close()

    return results


def output_path(output_dir: Path, date: datetime) -> Path:
    return output_dir / f"{date.strftime('%Y-%m-%d')}.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch crypto prices from CoinGecko")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Directory to write price JSON files",
    )
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    prices = fetch_prices(COINS)

    payload = {
        "date": now.date().isoformat(),
        "fetched_at": now.isoformat(),
        "prices": prices,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_path(args.output_dir, now)
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    print(f"Saved prices to {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
