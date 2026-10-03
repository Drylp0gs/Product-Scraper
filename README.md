# Product Data Scraper

A flexible Python web scraper designed to extract product details (name, category, SKU, price, availability, and URL) from e-commerce listing pages and save them to CSV.

It automatically attempts to parse structured `JSON-LD` metadata first. If unavailable, it falls back to configurable CSS selectors to parse product card elements.

---

## Features

- **JSON-LD Support:** Automatically extracts schema-compliant product data without manual CSS selectors.
- **Customizable Selectors:** Supports fallback CSS selectors for websites without structured metadata.
- **Pagination Support:** Crawls through multiple pages sequentially with configurable rate-limiting delays.
- **UTF-8 CSV Output:** Exports clean product data formatted ready for Excel, Pandas, or database imports.

---

## Requirements

- Python 3.7 or higher
- `requests`
- `beautifulsoup4`

---

## Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Drylp0gs/product-data-scraper.git

# Linux/macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate



pip install -r requirements.txt

# USAGE

python scraper.py "[https://example.com/shop](https://example.com/shop)" --output products.csv

# Custom CSS Selectors
If automatic detection misses fields on non-structured websites, specify target CSS selectors:
python scraper.py "[https://example.com/shop](https://example.com/shop)" \
  --card ".product-card" \
  --name ".product-title" \
  --price ".price" \
  --sku "[data-sku]" \
  --category ".category" \
  --availability ".stock-status" \
  --output custom_products.csv


# Handling PaginationScrape

multiple pages using the next-page link selector, maximum page limit, and custom delay between requests:Bashpython scraper.py "[https://example.com/shop](https://example.com/shop)" \
  --next "a.next-page" \
  --max-pages 5 \
  --delay 2.5
  
CLI OptionsArgumentDescriptionDefaulturlTarget product listing URL (required)
—-o, --outputOutput CSV filenameproducts.csv
--cardCSS selector for individual product card containersAutomatic
--nameCSS selector for product title/nameAutomatic
--priceCSS selector for product priceAutomatic
--skuCSS selector for product SKU/identifierAutomatic
--categoryCSS selector for product categoryAutomatic
--availabilityCSS selector for stock statusAutomatic
--nextCSS selector for the next page linkNone
--max-pagesMaximum listing pages to visit1
--delayDelay in seconds between page requests2.0
--timeoutHTTP request timeout in seconds20.0

# LicenseThis project is open-source and available under the MIT License.
