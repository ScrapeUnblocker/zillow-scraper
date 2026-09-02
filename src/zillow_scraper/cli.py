"""Command-line interface for zillow-scraper."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from . import __version__
from .scraper import ZillowScraper, filter_listings, listings_to_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zillow-scraper",
        description="Scrape Zillow real estate listings as clean JSON or CSV, "
        "powered by ScrapeUnblocker.",
    )
    parser.add_argument(
        "location",
        help='A place ("Austin, TX", "90210") or a full Zillow search URL.',
    )
    parser.add_argument(
        "-p",
        "--pages",
        type=int,
        default=1,
        help="Number of result pages to collect (default: 1).",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=("json", "csv"),
        default="json",
        help="Output format (default: json).",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Write to this file instead of stdout.",
    )
    parser.add_argument(
        "-c",
        "--country",
        default="US",
        help="ISO country code to route through (default: US).",
    )
    parser.add_argument("--min-price", type=int, help="Drop listings below this price.")
    parser.add_argument("--max-price", type=int, help="Drop listings above this price.")
    parser.add_argument("--min-beds", type=float, help="Drop listings with fewer beds.")
    parser.add_argument(
        "--api-key",
        help="ScrapeUnblocker API key (else read from SCRAPEUNBLOCKER_KEY).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    scraper = ZillowScraper(api_key=args.api_key, proxy_country=args.country)
    listings = scraper.search(args.location, pages=args.pages)
    listings = filter_listings(
        listings,
        min_price=args.min_price,
        max_price=args.max_price,
        min_beds=args.min_beds,
    )

    if args.format == "csv":
        rendered = listings_to_csv(listings)
    else:
        rendered = json.dumps([home.as_dict() for home in listings], indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="") as handle:
            handle.write(rendered)
        print(f"Wrote {len(listings)} listings to {args.output}", file=sys.stderr)
    else:
        print(rendered)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
