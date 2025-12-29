# Crypto Price Tracker

This repo runs a daily GitHub Action that scrapes current crypto prices from CoinGecko using Playwright and stores them as JSON files in `data/`.

## What it does

- Runs on a daily schedule (UTC) or manually via workflow dispatch
- Scrapes prices for a small set of coins from CoinGecko
- Writes a JSON snapshot to `data/YYYY-MM-DD.json`
- Commits the new snapshot back to the repo

## Data format

Each snapshot includes the fetch timestamp and a `prices` map keyed by coin slug:

```json
{
  "date": "2024-01-02",
  "fetched_at": "2024-01-02T00:00:00+00:00",
  "prices": {
    "bitcoin": {
      "name": "Bitcoin",
      "raw": "$42,123.45",
      "usd": 42123.45,
      "url": "https://www.coingecko.com/en/coins/bitcoin"
    }
  }
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
- [ ] kraken.com/prices
- [ ] finance.yahoo.com
- [ ] binance.com
- [ ] coinmarketcap.com
- [ ] coindesk.com
