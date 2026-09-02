"""Collect several pages of listings and write them to a CSV file.

Run:
    export SCRAPEUNBLOCKER_KEY=your_key_here
    python examples/export_csv.py "San Francisco, CA" 3 homes.csv
"""

from __future__ import annotations

import sys

from zillow_scraper import ZillowScraper, listings_to_csv


def main() -> None:
    location = sys.argv[1] if len(sys.argv) > 1 else "San Francisco, CA"
    pages = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    out_path = sys.argv[3] if len(sys.argv) > 3 else "homes.csv"

    scraper = ZillowScraper()
    listings = scraper.search(location, pages=pages)

    with open(out_path, "w", encoding="utf-8", newline="") as handle:
        handle.write(listings_to_csv(listings))

    print(f"Wrote {len(listings)} listings from {pages} page(s) to {out_path}")


if __name__ == "__main__":
    main()
