#!/usr/bin/env python3
import json
import re
from playwright.sync_api import sync_playwright

URL = "https://www.binance.com/en/markets/overview"


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def handle_response(response):
            try:
                content_type = response.headers.get("content-type", "")
            except Exception:
                content_type = ""
            if "application/json" not in content_type:
                return
            url = response.url
            if "binance" not in url:
                return
            try:
                data = response.json()
            except Exception:
                return
            text = json.dumps(data)
            for token in ["BTC", "ETH", "SOL", "ADA", "ARB", "XMR", "BNB"]:
                if token in text:
                    print("json response", url)
                    print("json snippet", text[:500])
                    return

        page.on("response", handle_response)
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(6000)

        print("Loaded", page.url)
        print("Title", page.title())

        symbols = ["BTC", "ETH", "SOL", "ADA", "ARB", "XMR", "BNB"]
        static_url = "https://www.binance.com/bapi/asset/v2/friendly/asset-service/product/get-product-static?includeEtf=true"
        dynamic_url = "https://www.binance.com/bapi/asset/v2/friendly/asset-service/product/get-product-dynamic?includeEtf=true"
        static_res = page.request.get(static_url)
        dynamic_res = page.request.get(dynamic_url)
        if static_res.ok and dynamic_res.ok:
            static_data = static_res.json().get("data", [])
            dynamic_data = dynamic_res.json().get("data", [])
            dynamic_map = {item.get("s"): item for item in dynamic_data}
            for item in static_data:
                if item.get("q") != "USDT":
                    continue
                if item.get("b") not in symbols:
                    continue
                symbol_pair = item.get("s")
                dynamic = dynamic_map.get(symbol_pair, {})
                print("pair", symbol_pair, "base", item.get("b"), "name", item.get("an"), "price", dynamic.get("c"))

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

        for coin in ["Bitcoin", "Ethereum", "Solana", "Cardano", "Arbitrum", "Monero", "BNB"]:
            loc = page.locator(f"text={coin}")
            print(coin, "text nodes", loc.count())

        html = page.content()
        print("html length", len(html))
        print("html head", html[:500].replace("\n", " "))
        for token in ["price", "current", "usd", "$"]:
            if token in html:
                print("found token", token)

        # Scroll to load more rows if lazy-loaded
        for i in range(5):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)
        print("after scroll URL", page.url)

        dollar = page.locator("text=/\\$[0-9]/")
        print("dollar elements", dollar.count())
        for i in range(min(5, dollar.count())):
            print("dollar", i, dollar.nth(i).inner_text().strip())

        for selector in ["[data-testid*='price']", "[data-symbol]", "[data-quote]", "[data-field]", "[data-bn-type]", "a[href*='/price/']"]:
            loc = page.locator(selector)
            if loc.count():
                print("selector", selector, "count", loc.count())
                for i in range(min(5, loc.count())):
                    print(loc.nth(i).inner_text().strip())

        # Find anchors containing coin names and inspect nearby text
        slug_map = {
            "bitcoin": "Bitcoin",
            "ethereum": "Ethereum",
            "solana": "Solana",
            "cardano": "Cardano",
            "arbitrum": "Arbitrum",
            "monero": "Monero",
            "bnb": "BNB",
        }

        for slug, coin in slug_map.items():
            anchor = page.locator(f"a[href*='/price/{slug}']")
            print(coin, "anchors by slug", anchor.count())
            if anchor.count():
                first = anchor.first
                text = first.inner_text().strip()
                href = first.get_attribute("href")
                print(coin, "anchor text", text)
                print(coin, "anchor href", href)
                parent = first.locator("xpath=..")
                if parent.count():
                    print(coin, "parent text", parent.first.inner_text().strip())
                container = first.locator("xpath=ancestor::div[contains(@class,'css') or contains(@class,'Row')]")
                print(coin, "container count", container.count())
                if container.count():
                    print(coin, "container text", container.first.inner_text().strip())

        # Look for JSON state in scripts
        scripts = page.locator("script")
        print("script count", scripts.count())
        for i in range(min(5, scripts.count())):
            text = scripts.nth(i).inner_text().strip()
            if "price" in text or "markets" in text:
                print("script", i, "length", len(text))
                snippet = text[:500]
                print("script head", snippet.replace("\n", " "))

        for selector in ["script#__NEXT_DATA__", "script[type='application/json']"]:
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
