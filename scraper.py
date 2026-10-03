#!/usr/bin/env python3
"""
Product Data Scraper
Collects product name, category, SKU, price, and availability from public
product/listing pages and saves the results to CSV.

Install:
    python -m pip install requests beautifulsoup4

Example:
    python scraper.py "https://example.com/shop" --output products.csv

If automatic detection misses fields, supply CSS selectors:
    python scraper.py "https://example.com/shop" \
      --card ".product-card" \
      --name ".product-title" \
      --price ".price" \
      --sku "[data-sku]" \
      --category ".category" \
      --availability ".stock-status"

This script does not bypass logins, CAPTCHAs, paywalls, or anti-bot controls.
Use only on sites you are allowed to access, and follow their terms and
robots.txt. Some JavaScript-heavy sites need an official API or a permitted
browser-based approach; this requests/BeautifulSoup script does not run JS.
"""

import argparse
import csv
import json
import re
import sys
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ProductDataScraper/1.0; "
        "+https://example.com/bot)"
    )
}

FIELDS = ["product_name", "category", "sku", "price", "availability", "url"]


def clean(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def text_from(node, selector):
    if not selector:
        return ""
    found = node.select_one(selector)
    if not found:
        return ""
    # Prefer useful attributes for common price/SKU elements.
    for attr in ("content", "data-price", "data-sku", "value", "aria-label"):
        value = found.get(attr)
        if value:
            return clean(value)
    return clean(found.get_text(" ", strip=True))


def first_text(node, selectors):
    for selector in selectors:
        value = text_from(node, selector)
        if value:
            return value
    return ""


def walk_json(value):
    """Yield dictionaries nested in JSON-LD structures."""
    if isinstance(value, dict):
        yield value
        graph = value.get("@graph")
        if graph:
            yield from walk_json(graph)
        for key, child in value.items():
            if key != "@graph" and isinstance(child, (dict, list)):
                yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def product_from_jsonld(soup, page_url):
    products = []
    seen = set()

    for tag in soup.select('script[type="application/ld+json"]'):
        raw = tag.string or tag.get_text()
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue

        for item in walk_json(data):
            item_type = item.get("@type", [])
            if isinstance(item_type, str):
                types = [item_type.lower()]
            else:
                types = [str(x).lower() for x in item_type]
            if not any("product" in t for t in types):
                continue

            name = clean(item.get("name"))
            if not name:
                continue

            offers = item.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            if not isinstance(offers, dict):
                offers = {}

            price = clean(offers.get("price") or offers.get("lowPrice"))
            currency = clean(offers.get("priceCurrency"))
            if price and currency and currency not in price:
                price = f"{currency} {price}"

            availability = clean(offers.get("availability"))
            if "/" in availability:
                availability = availability.rsplit("/", 1)[-1]
            category = item.get("category", "")
            if isinstance(category, list):
                category = " > ".join(map(str, category))

            url = clean(item.get("url"))
            if url:
                url = urljoin(page_url, url)

            sku = clean(item.get("sku") or item.get("mpn"))
            key = (name.lower(), url or page_url)
            if key in seen:
                continue
            seen.add(key)
            products.append({
                "product_name": name,
                "category": clean(category),
                "sku": sku,
                "price": price,
                "availability": availability,
                "url": url or page_url,
            })
    return products


def guess_cards(soup):
    selectors = [
        '[itemtype*="Product"]',
        '[class*="product-card"]',
        '[class*="product_item"]',
        '[class*="product-item"]',
        '[class*="product"]',
        "article",
    ]
    for selector in selectors:
        cards = soup.select(selector)
        # Avoid selecting a huge number of generic nested product elements.
        if cards and len(cards) <= 500:
            return cards
    return []


def scrape_cards(soup, page_url, args):
    cards = soup.select(args.card) if args.card else guess_cards(soup)
    results = []

    name_selectors = [args.name] if args.name else [
        '[itemprop="name"]', "h2", "h3", ".product-title",
        "[class*='product-title']", "a[title]"
    ]
    price_selectors = [args.price] if args.price else [
        '[itemprop="price"]', "[class*='price']", ".price"
    ]
    sku_selectors = [args.sku] if args.sku else [
        '[itemprop="sku"]', "[data-sku]", "[class*='sku']"
    ]
    category_selectors = [args.category] if args.category else [
        '[itemprop="category"]', "[class*='category']"
    ]
    availability_selectors = [args.availability] if args.availability else [
        '[itemprop="availability"]', "[class*='stock']",
        "[class*='availability']"
    ]

    for card in cards:
        name = first_text(card, name_selectors)
        if not name:
            continue

        price = first_text(card, price_selectors)
        sku = first_text(card, sku_selectors)
        category = first_text(card, category_selectors)
        availability = first_text(card, availability_selectors)

        link = card.select_one("a[href]")
        product_url = urljoin(page_url, link["href"]) if link else page_url

        # Clean common schema.org availability URLs.
        if availability and "/" in availability:
            availability = availability.rsplit("/", 1)[-1]

        results.append({
            "product_name": name,
            "category": category,
            "sku": sku,
            "price": price,
            "availability": availability,
            "url": product_url,
        })
    return results


def get_page(session, url, timeout):
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def scrape(args):
    session = requests.Session()
    session.headers.update(HEADERS)
    current_url = args.url
    visited = set()
    all_rows = []
    page_number = 0

    while current_url and current_url not in visited and page_number < args.max_pages:
        visited.add(current_url)
        page_number += 1
        print(f"[{page_number}/{args.max_pages}] Fetching {current_url}")

        try:
            soup = get_page(session, current_url, args.timeout)
        except requests.RequestException as exc:
            print(f"Request failed: {exc}", file=sys.stderr)
            break

        # Structured Product data is generally more reliable than guessed CSS.
        rows = product_from_jsonld(soup, current_url)
        if not rows:
            rows = scrape_cards(soup, current_url, args)

        all_rows.extend(rows)
        print(f"  Found {len(rows)} product(s)")

        if not args.next or page_number >= args.max_pages:
            break
        next_link = soup.select_one(args.next)
        current_url = (
            urljoin(current_url, next_link.get("href", ""))
            if next_link and next_link.get("href")
            else ""
        )
        if current_url:
            time.sleep(args.delay)

    # Deduplicate by product URL + name.
    unique = {}
    for row in all_rows:
        key = (row["url"], row["product_name"].lower())
        unique[key] = row
    rows = list(unique.values())

    with open(args.output, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone. Saved {len(rows)} product(s) to: {args.output}")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape product listing data into a CSV file."
    )
    parser.add_argument("url", help="Public product listing page URL")
    parser.add_argument("-o", "--output", default="products.csv",
                        help="Output CSV filename (default: products.csv)")
    parser.add_argument("--card", help="CSS selector for each product card")
    parser.add_argument("--name", help="CSS selector for product name")
    parser.add_argument("--category", help="CSS selector for category")
    parser.add_argument("--sku", help="CSS selector for SKU")
    parser.add_argument("--price", help="CSS selector for price")
    parser.add_argument("--availability", help="CSS selector for stock/status")
    parser.add_argument("--next", help="CSS selector for the next-page link")
    parser.add_argument("--max-pages", type=int, default=1,
                        help="Maximum listing pages to visit (default: 1)")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Delay between pages in seconds (default: 2)")
    parser.add_argument("--timeout", type=float, default=20,
                        help="HTTP timeout in seconds (default: 20)")
    args = parser.parse_args()

    if urlparse(args.url).scheme not in ("http", "https"):
        parser.error("URL must start with http:// or https://")
    if args.max_pages < 1 or args.delay < 0 or args.timeout <= 0:
        parser.error("--max-pages must be >= 1, --delay >= 0, --timeout > 0")

    scrape(args)


if __name__ == "__main__":
    main()
