"""Offline unit tests. The ScrapeUnblocker SDK is mocked - no API credit spent."""

from __future__ import annotations

import pytest
from scrapeunblocker import ParsedPage, ScrapeTimeoutError, UpstreamOutageError

from zillow_scraper import Listing, ZillowScraper, listings_to_csv
from zillow_scraper.scraper import (
    filter_listings,
    location_to_url,
    normalize_item,
    paginate_url,
)

RAW_ITEM = {
    "zpid": 29369311,
    "listing_url": "https://www.zillow.com/homedetails/6305-Leatherwood-Cv/29369311_zpid/",
    "image_url": "https://photos.zillowstatic.com/x.jpg",
    "price": {"value": 750000, "currency": "USD"},
    "price_raw": {"value": 750000, "currency": None},
    "address": "6305 Leatherwood Cv, Austin, TX 78759",
    "address_city": "Austin",
    "address_state": "TX",
    "address_zipcode": "78759",
    "beds": 4,
    "baths": 3,
    "area_sqft": 2164,
    "status": "Active",
    "home_type": "SINGLE_FAMILY",
    "days_on_zillow": 12,
    "broker_name": "Keller Williams Realty",
    "latitude": 30.41,
    "longitude": -97.75,
    "zestimate": None,
    "marketing_status": "For Sale",
}


class FakeClient:
    """Stand-in for scrapeunblocker.Client that returns canned pages."""

    def __init__(self, pages):
        # pages: list of item-lists, one per get_parsed call
        self._pages = list(pages)
        self.calls = []

    def get_parsed(self, url, *, proxy_country=None):
        self.calls.append((url, proxy_country))
        items = self._pages.pop(0) if self._pages else []
        return ParsedPage(page_type="search_list", source=None, data={"items": items}, raw={})


def test_normalize_flattens_price_and_labels_fields():
    listing = normalize_item(RAW_ITEM)
    assert listing.zpid == "29369311"
    assert listing.price == 750000
    assert listing.currency == "USD"
    assert listing.city == "Austin"
    assert listing.state == "TX"
    assert listing.zipcode == "78759"
    assert listing.beds == 4.0
    assert listing.area_sqft == 2164
    assert listing.home_type == "SINGLE_FAMILY"
    # unknown keys are preserved but do not pollute the typed surface
    assert listing.extra["marketing_status"] == "For Sale"


def test_normalize_price_fallback_and_string_prices():
    item = {"zpid": 1, "price": None, "price_raw": {"value": "1,250,000", "currency": "USD"}}
    listing = normalize_item(item)
    assert listing.price == 1250000


def test_location_to_url_builds_slug():
    assert location_to_url("Austin, TX") == ("https://www.zillow.com/homes/for_sale/Austin-TX_rb/")
    assert location_to_url("San Francisco, CA").endswith("San-Francisco-CA_rb/")


def test_location_to_url_passes_through_urls():
    url = "https://www.zillow.com/homes/for_sale/Austin-TX_rb/?searchQueryState=x"
    assert location_to_url(url) == url


def test_paginate_url():
    base = "https://www.zillow.com/homes/for_sale/Austin-TX_rb/"
    assert paginate_url(base, 1) == base
    assert paginate_url(base, 2) == base + "2_p/"
    assert paginate_url(base.rstrip("/"), 3) == base + "3_p/"


def test_search_collects_multiple_pages():
    client = FakeClient([[RAW_ITEM], [dict(RAW_ITEM, zpid=2)]])
    scraper = ZillowScraper(client=client)
    listings = scraper.search("Austin, TX", pages=2)
    assert [home.zpid for home in listings] == ["29369311", "2"]
    # page 2 URL carries the pagination segment
    assert client.calls[1][0].endswith("2_p/")
    assert client.calls[0][1] == "US"


def test_search_stops_on_empty_page():
    client = FakeClient([[RAW_ITEM], []])
    scraper = ZillowScraper(client=client)
    listings = scraper.search("Austin, TX", pages=5)
    assert len(listings) == 1
    assert len(client.calls) == 2  # stopped after the empty page, not 5


def test_retry_on_transient_then_success():
    class FlakyClient:
        def __init__(self):
            self.attempts = 0

        def get_parsed(self, url, *, proxy_country=None):
            self.attempts += 1
            if self.attempts < 3:
                raise UpstreamOutageError("upstream hiccup", status_code=503)
            return ParsedPage("search_list", None, {"items": [RAW_ITEM]}, {})

    scraper = ZillowScraper(client=FlakyClient(), max_retries=3)
    scraper._sleep = lambda _s: None  # don't actually sleep in tests
    listings = scraper.search("Austin, TX")
    assert len(listings) == 1


def test_retry_gives_up_and_raises():
    class DeadClient:
        def get_parsed(self, url, *, proxy_country=None):
            # ScrapeTimeoutError does NOT take a status_code kwarg
            raise ScrapeTimeoutError("timed out")

    scraper = ZillowScraper(client=DeadClient(), max_retries=2)
    scraper._sleep = lambda _s: None
    with pytest.raises(ScrapeTimeoutError):
        scraper.search("Austin, TX")


def test_filter_listings():
    homes = [
        Listing(zpid="a", price=500_000, beds=2),
        Listing(zpid="b", price=800_000, beds=4),
        Listing(zpid="c", price=None, beds=3),
    ]
    kept = filter_listings(homes, min_price=600_000, max_price=900_000, min_beds=3)
    assert [h.zpid for h in kept] == ["b"]


def test_listings_to_csv_has_header_and_rows():
    csv_text = listings_to_csv([normalize_item(RAW_ITEM)])
    lines = csv_text.strip().splitlines()
    assert lines[0].startswith("zpid,address,city,state,zipcode,price,currency")
    assert "Austin" in lines[1]
    assert "750000" in lines[1]
