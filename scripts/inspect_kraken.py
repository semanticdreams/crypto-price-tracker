#!/usr/bin/env python3
import json
import re
from playwright.sync_api import sync_playwright

URL = "https://www.kraken.com/prices"


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(12000)

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

        # Look for coin text anywhere on the page
        for coin in ["Bitcoin", "Ethereum", "Solana", "Cardano", "Arbitrum", "Monero", "BNB"]:
            loc = page.locator(f"text={coin}")
            print(coin, "text nodes", loc.count())
            if loc.count():
                for i in range(min(2, loc.count())):
                    box = loc.nth(i).bounding_box()
                    print(coin, "bbox", box)

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

        for selector in ["[data-testid*='price']", "[data-testid*='Price']", "[data-price]"]:
            loc = page.locator(selector)
            if loc.count():
                print("selector", selector, "count", loc.count())
                for i in range(min(5, loc.count())):
                    print(loc.nth(i).inner_text().strip())

        # Inspect currency selector
        combo = page.get_by_role("combobox").first
        if combo.count():
            print("combobox found")
            try:
                combo.click()
                page.wait_for_timeout(1000)
                options = page.get_by_role("option")
                print("option count", options.count())
                for i in range(min(10, options.count())):
                    print("option", i, options.nth(i).inner_text().strip())
            except Exception as exc:
                print("combobox error", exc)

        currency_button = page.locator(
            "button[data-testid='prices-table-currency-selector-button']:visible"
        )
        print("currency button count", currency_button.count())

        # Try switching to USD and re-read BTC row
        try:
            if currency_button.count():
                currency_button.first.click()
                page.wait_for_timeout(1000)
                options = page.locator("[role='option']")
                print("option count after click", options.count())
                for i in range(min(10, options.count())):
                    print("option", i, options.nth(i).inner_text().strip())

                usd_option = options.filter(has_text="USD")
                if usd_option.count():
                    usd_option.first.click()
                    page.wait_for_timeout(2000)
                    rows = page.locator("table tbody tr")
                    btc_row = rows.filter(has_text="Bitcoin").first
                    if btc_row.count():
                        price_cell = btc_row.locator("td").nth(2).inner_text().strip()
                        print("BTC price after USD select", price_cell)
        except Exception as exc:
            print("USD select error", exc)

        for selector in ["script#__NEXT_DATA__", "script#__NUXT_DATA__", "script[type='application/json']"]:
            loc = page.locator(selector)
            if loc.count():
                raw = loc.first.inner_text()
                print("script", selector, "length", len(raw))
                if selector == "script#__NEXT_DATA__":
                    try:
                        data = json.loads(raw)
                        raw_str = json.dumps(data)
                        match = re.search(r"price[^0-9]*([0-9]+\\.[0-9]+)", raw_str)
                        print("price match", match.group(1) if match else None)
                    except json.JSONDecodeError as exc:
                        print("next_data json error", exc)

        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
