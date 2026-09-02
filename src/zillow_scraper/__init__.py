"""zillow-scraper - scrape Zillow real estate listings as clean JSON.

Powered by ScrapeUnblocker (https://scrapeunblocker.com) - this package turns a
Zillow "for sale" search into a list of normalized :class:`Listing` records
(price, beds, baths, area, address, home type, Zestimate, broker and
geolocation) using the ScrapeUnblocker ``getPageSource`` parsed_data endpoint.

Example
-------
    from zillow_scraper import ZillowScraper

    scraper = ZillowScraper()  # reads SCRAPEUNBLOCKER_KEY
    for home in scraper.search("Austin, TX", pages=2):
        print(home.address, home.price, home.beds, home.baths)
"""

from __future__ import annotations

from .scraper import Listing, ZillowScraper, listings_to_csv

__all__ = ["Listing", "ZillowScraper", "listings_to_csv", "__version__"]

__version__ = "0.1.0"
