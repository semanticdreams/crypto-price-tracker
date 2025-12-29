#!/usr/bin/env python3
import json
import re
from playwright.sync_api import sync_playwright

URL = "https://www.coingecko.com/"


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        print("Loaded", page.url)

        rows = page.locator("table tbody tr")
        print("row count", rows.count())

        for coin in ["Bitcoin", "Ethereum", "Solana", "Cardano"]:
            row = rows.filter(has_text=coin)
            print(coin, "rows", row.count())
            if row.count():
                tds = row.first.locator("td")
                print("td count", tds.count())
                for i in range(min(12, tds.count())):
                    text = tds.nth(i).inner_text().strip()
                    if text:
                        print(coin, "td", i, text)

        # Try to detect price-like tokens in DOM
        html = page.content()
        for token in ["price", "current", "usd", "$"]:
            if token in html:
                print("found token", token)

        # Try to find dollar text nodes
        dollar = page.locator("text=/\\$[0-9]/")
        print("dollar elements", dollar.count())
        for i in range(min(5, dollar.count())):
            print("dollar", i, dollar.nth(i).inner_text().strip())

        # Check for data blobs
        next_data = page.locator("script#__NEXT_DATA__")
        if next_data.count():
            raw = next_data.first.inner_text()
            print("next_data length", len(raw))
            try:
                data = json.loads(raw)
                raw_str = json.dumps(data)
                match = re.search(r"current_price[^0-9]*([0-9]+\\.[0-9]+)", raw_str)
                print("current_price match", match.group(1) if match else None)
            except json.JSONDecodeError as exc:
                print("next_data json error", exc)

        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
