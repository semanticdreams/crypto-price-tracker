# Crypto Price Tracker

[![Fetch crypto prices daily](https://github.com/semanticdreams/crypto-price-tracker/actions/workflows/fetch.yml/badge.svg)](https://github.com/semanticdreams/crypto-price-tracker/actions/workflows/fetch.yml)

This repo runs a daily GitHub Action that scrapes current crypto prices from multiple sources (CoinGecko, Kraken, Yahoo Finance, Binance, CoinMarketCap, CoinDesk) using Playwright and stores them as JSON files in `data/`.

## What it does

- Runs on a daily schedule (UTC) or manually via workflow dispatch
- Scrapes prices for a small set of coins from CoinGecko, Kraken, Yahoo Finance, Binance, CoinMarketCap, and CoinDesk
- Writes a JSON snapshot to `data/YYYY-MM-DD.json`
- Commits the new snapshot back to the repo

## Data format

Each snapshot includes the fetch timestamp and a flat `quotes` list. Each quote includes the coin identifiers plus `source`, `price`, and `currency`. If any scraper fails, the run still writes output and records the error in `errors`.

```json
{
  "date": "2024-01-02",
  "fetched_at": "2024-01-02T00:00:00+00:00",
  "sources": [
    "coingecko",
    "kraken",
    "yahoo",
    "binance",
    "coinmarketcap",
    "coindesk"
  ],
  "errors": [],
  "quotes": [
    {
      "slug": "bitcoin",
      "symbol": "BTC",
      "name": "Bitcoin",
      "source": "coingecko",
      "raw": "$42,123.45",
      "price": 42123.45,
      "currency": "USD",
      "url": "https://www.coingecko.com/"
    },
    {
      "slug": "bitcoin",
      "symbol": "BTC",
      "name": "Bitcoin",
      "source": "kraken",
      "raw": "€39,100.00",
      "price": 39100.0,
      "currency": "EUR",
      "url": "https://www.kraken.com/prices"
    }
  ]
}
```

## Local usage

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
python fetch_prices.py
```

## Tests

```bash
pytest
```

## Configuration

Edit the `COINS` list in `fetch_prices.py` to add or remove coins.



## Sources

- [x] coingecko.com
- [x] kraken.com/prices
- [x] finance.yahoo.com
- [x] binance.com
- [x] coinmarketcap.com
- [x] coindesk.com
