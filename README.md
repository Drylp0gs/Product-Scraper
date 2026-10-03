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
   git clone [https://github.com/Drylp0gs/product-data-scraper.git](https://github.com/YOUR-USERNAME/product-data-scraper.git)
   cd product-data-scraper
