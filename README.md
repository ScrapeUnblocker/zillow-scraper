# zillow-scraper

[![CI](https://github.com/ScrapeUnblocker/zillow-scraper/actions/workflows/ci.yml/badge.svg)](https://github.com/ScrapeUnblocker/zillow-scraper/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Scrape **Zillow** real estate listings as clean, structured JSON or CSV — price,
beds, baths, area, address, home type, Zestimate, broker and geolocation — with a
CLI and a small Python library.

> **Powered by [ScrapeUnblocker](https://scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos).**
> Zillow sits behind heavy anti-bot protection. Instead of fighting it, this
> library asks ScrapeUnblocker's `getPageSource` endpoint to render the search
> page and return **AI-parsed structured data**, so you get typed listing records
> without writing or maintaining any HTML selectors.

## Features

- 🏡 **Structured listings** — every result normalized to a typed `Listing`
  (price, beds, baths, sqft, address parts, home type, status, Zestimate,
  broker, lat/long, listing URL, image).
- 📄 **Multi-page collection** — walk several result pages in one call; stops
  automatically when results run out.
- 🧭 **Search by place or URL** — pass `"Austin, TX"` / `"90210"` or paste a full
  Zillow search URL (with your own filters).
- 🔎 **Client-side filtering** — narrow by min/max price and minimum bedrooms.
- 🧰 **JSON & CSV output** — from the CLI or the library.
- ♻️ **Automatic retries** — transient rate-limit / timeout / upstream errors are
  retried with exponential backoff.
- ✅ **No selectors to maintain** — parsing is handled server-side.

## Install

```bash
pip install .
# or, for development:
pip install -e ".[dev]"
```

Set your API key (get one from
[ScrapeUnblocker](https://scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos)):

```bash
cp .env.example .env
export SCRAPEUNBLOCKER_KEY=your_key_here
```

The SDK reads the key from the `SCRAPEUNBLOCKER_KEY` environment variable.

## CLI usage

```bash
# One page of Austin listings as JSON
zillow-scraper "Austin, TX"

# Three pages, CSV, written to a file
zillow-scraper "San Francisco, CA" --pages 3 --format csv --output homes.csv

# Filter as you scrape
zillow-scraper "78704" --pages 2 --min-price 400000 --max-price 900000 --min-beds 3
```

```
usage: zillow-scraper [-h] [-p PAGES] [-f {json,csv}] [-o OUTPUT] [-c COUNTRY]
                      [--min-price MIN_PRICE] [--max-price MAX_PRICE]
                      [--min-beds MIN_BEDS] [--api-key API_KEY] [--version]
                      location
```

## Library usage

```python
from zillow_scraper import ZillowScraper

scraper = ZillowScraper()  # reads SCRAPEUNBLOCKER_KEY

for home in scraper.search("Austin, TX", pages=2):
    print(home.price, home.beds, home.baths, home.address)

# Or grab them all and export to CSV
from zillow_scraper import listings_to_csv

listings = scraper.search("90210", pages=1)
open("beverly-hills.csv", "w").write(listings_to_csv(listings))
```

## Example output

```json
[
  {
    "zpid": "29369311",
    "address": "6305 Leatherwood Cv, Austin, TX 78759",
    "city": "Austin",
    "state": "TX",
    "zipcode": "78759",
    "price": 750000,
    "currency": "USD",
    "beds": 4.0,
    "baths": 3.0,
    "area_sqft": 2164,
    "home_type": "SINGLE_FAMILY",
    "status": "Active",
    "zestimate": null,
    "days_on_zillow": 12,
    "broker_name": "Keller Williams Realty",
    "latitude": 30.41,
    "longitude": -97.75,
    "listing_url": "https://www.zillow.com/homedetails/6305-Leatherwood-Cv-Austin-TX-78759/29369311_zpid/"
  }
]
```

## Project layout

```
src/zillow_scraper/
  __init__.py     package exports + version
  scraper.py      ZillowScraper, Listing, normalization / pagination / CSV helpers
  cli.py          argparse command-line interface
examples/         runnable scripts (JSON, CSV export, price filter)
tests/            offline unit tests (the SDK is mocked - no API credit spent)
```

## Development

```bash
make install   # editable install with dev extras
make lint      # ruff check
make format    # ruff format
make test      # pytest (fully offline)
make run       # sample scrape
```

The test suite mocks the ScrapeUnblocker SDK, so `make test` spends **no** API
credit and needs no key. CI runs lint + tests on Python 3.11 and 3.13.

## How it works

`ZillowScraper.search()` builds a Zillow "for sale" URL from your query, then
calls the ScrapeUnblocker
[`getPageSource`](https://docs.scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos)
endpoint with parsed-data extraction enabled (via the official
[`scrapeunblocker`](https://pypi.org/project/scrapeunblocker/) SDK). ScrapeUnblocker
renders the page and returns structured listing records, which this library maps
onto the typed `Listing` dataclass and (optionally) flattens to CSV.

## Links

- 🌐 Product: https://scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos
- 📚 Docs: https://docs.scrapeunblocker.com/?utm_source=github&utm_medium=integration&utm_campaign=example-repos

## Legal

This project is an integration example. Scrape responsibly: review Zillow's Terms
of Service and `robots.txt`, respect rate limits, and only collect data you are
permitted to use.

## License

[MIT](LICENSE) © 2026 ScrapeUnblocker
