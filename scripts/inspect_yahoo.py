#!/usr/bin/env python3
import json
import re
from playwright.sync_api import sync_playwright

URL = "https://finance.yahoo.com/markets/crypto/all/?start=0&count=100"


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        if "consent.yahoo.com" in page.url:
            print("consent page detected", page.url)
            buttons = page.locator("button")
            print("button count", buttons.count())
            for i in range(min(10, buttons.count())):
                text = buttons.nth(i).inner_text().strip()
                if text:
                    print("button", i, text)
            for label in [
                "Accept",
                "Accept all",
                "Agree",
                "I agree",
                "Elfogadom",
                "Az osszes elfogadasa",
                "Az összes elfogadása",
            ]:
                candidate = page.locator(f"button:has-text('{label}')")
                if candidate.count():
                    candidate.first.click()
                    page.wait_for_timeout(3000)
                    break

            if "consent.yahoo.com" in page.url and buttons.count():
                buttons.first.click()
                page.wait_for_timeout(3000)

            if "consent.yahoo.com" in page.url:
                page.goto(URL, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(5000)

        print("Loaded", page.url)
        print("Title", page.title())

        rows = page.locator("table tbody tr")
        print("row count", rows.count())

        for coin in ["Bitcoin", "Ethereum", "Solana", "Cardano", "Arbitrum", "Monero", "BNB"]:
            row = rows.filter(has_text=coin)
            print(coin, "rows", row.count())
            if row.count():
                tds = row.first.locator("td")
                print("td count", tds.count())
                for i in range(min(12, tds.count())):
                    text = tds.nth(i).inner_text().strip()
                    if text:
                        print(coin, "td", i, text)

        html = page.content()
        print("html length", len(html))
        print("html head", html[:500].replace("\n", " "))
        for token in ["price", "current", "usd", "$"]:
            if token in html:
                print("found token", token)

        dollar = page.locator("text=/\\$[0-9]/")
        print("dollar elements", dollar.count())
        for i in range(min(5, dollar.count())):
            print("dollar", i, dollar.nth(i).inner_text().strip())

        for selector in ["[data-testid*='price']", "[data-symbol]", "[data-quote]", "[data-field]"]:
            loc = page.locator(selector)
            if loc.count():
                print("selector", selector, "count", loc.count())
                for i in range(min(5, loc.count())):
                    print(loc.nth(i).inner_text().strip())

        for selector in ["script#__NEXT_DATA__", "script[type='application/json']"]:
            loc = page.locator(selector)
            if loc.count():
                raw = loc.first.inner_text()
                print("script", selector, "length", len(raw))
                if selector == "script#__NEXT_DATA__":
                    try:
                        data = json.loads(raw)
                        raw_str = json.dumps(data)
                        match = re.search(r"regularMarketPrice[^0-9]*([0-9]+\\.[0-9]+)", raw_str)
                        print("regularMarketPrice match", match.group(1) if match else None)
                    except json.JSONDecodeError as exc:
                        print("next_data json error", exc)

        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
