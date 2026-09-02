"""Scrape listings and keep only those inside a price / bedroom window.

Run:
    export SCRAPEUNBLOCKER_KEY=your_key_here
    python examples/price_filter.py "Austin, TX"
"""

from __future__ import annotations

import sys

from zillow_scraper import ZillowScraper
from zillow_scraper.scraper import filter_listings


def main() -> None:
    location = sys.argv[1] if len(sys.argv) > 1 else "Austin, TX"

    scraper = ZillowScraper()
    listings = scraper.search(location, pages=2)

    affordable = filter_listings(
        listings,
        max_price=900_000,
        min_beds=3,
    )

    print(f"{len(affordable)} of {len(listings)} listings are <= $900k with 3+ beds:\n")
    for home in sorted(affordable, key=lambda h: h.price or 0):
        price = f"${home.price:,}" if home.price else "n/a"
        print(f"  {price:>12}  {home.beds}bd/{home.baths}ba  {home.address}")


if __name__ == "__main__":
    main()
