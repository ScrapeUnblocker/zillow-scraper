"""Fetch one page of Zillow listings and print them as JSON.

Run:
    export SCRAPEUNBLOCKER_KEY=your_key_here
    python examples/basic_search.py "Austin, TX"
"""

from __future__ import annotations

import json
import sys

from zillow_scraper import ZillowScraper


def main() -> None:
    location = sys.argv[1] if len(sys.argv) > 1 else "Austin, TX"

    scraper = ZillowScraper()  # reads SCRAPEUNBLOCKER_KEY
    listings = scraper.search(location, pages=1)

    print(f"Found {len(listings)} listings for {location!r}\n")
    print(json.dumps([home.as_dict() for home in listings[:5]], indent=2))


if __name__ == "__main__":
    main()
