#!/usr/bin/env python3
import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from scrapers import PriceResult, list_sources, merge_results
from scrapers.coingecko import CoinGeckoScraper
from scrapers.kraken import KrakenScraper
from scrapers.yahoo import YahooScraper
from scrapers.binance import BinanceScraper
from scrapers.coinmarketcap import CoinMarketCapScraper
from scrapers.coindesk import CoinDeskScraper


def output_path(output_dir: Path, date: datetime) -> Path:
    return output_dir / f"{date.strftime('%Y-%m-%d')}.json"


def serialize_prices(prices: List[PriceResult]) -> List[Dict[str, object]]:
    return [asdict(price) for price in prices]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch crypto prices from multiple sources"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Directory to write price JSON files",
    )
    args = parser.parse_args()

    scrapers = [
        CoinGeckoScraper(),
        KrakenScraper(),
        YahooScraper(),
        BinanceScraper(),
        CoinMarketCapScraper(),
        CoinDeskScraper(),
    ]

    errors: List[Dict[str, str]] = []
    collected = []
    for scraper in scrapers:
        try:
            collected.append((scraper.name, scraper.fetch()))
        except Exception as exc:
            errors.append({"source": scraper.name, "error": str(exc)})

    results = merge_results(collected)

    now = datetime.now(timezone.utc)
    payload = {
        "date": now.date().isoformat(),
        "fetched_at": now.isoformat(),
        "sources": list_sources(scrapers),
        "quotes": serialize_prices(results),
        "errors": errors,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_path(args.output_dir, now)
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    print(f"Saved prices to {destination}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
