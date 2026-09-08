"""Core scraping logic for zillow-scraper.

The public surface is :class:`ZillowScraper` plus the :class:`Listing` record it
returns. All network access goes through the official ScrapeUnblocker Python SDK
(``pip install scrapeunblocker``); nothing here talks to Zillow directly.
"""

from __future__ import annotations

import csv
import io
import time
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass, field
from typing import Any

from scrapeunblocker import (
    Client,
    RateLimitError,
    ScrapeTimeoutError,
    ServerError,
    UpstreamOutageError,
)

# ScrapeUnblocker errors that are worth retrying: transient upstream / rate
# limiting / timeout conditions. Everything else (auth, blocked, not-found,
# bad request) is surfaced immediately.
_TRANSIENT_ERRORS = (RateLimitError, ServerError, UpstreamOutageError, ScrapeTimeoutError)

_SEARCH_BASE = "https://www.zillow.com/homes/for_sale/{slug}_rb/"

# Product / docs links (UTM-tagged so referrals are attributable).
PRODUCT_URL = (
    "https://scrapeunblocker.com/?utm_source=github"
    "&utm_medium=integration&utm_campaign=example-repos"
)
DOCS_URL = (
    "https://docs.scrapeunblocker.com/?utm_source=github"
    "&utm_medium=integration&utm_campaign=example-repos"
)


@dataclass
class Listing:
    """A single Zillow "for sale" result, normalized to flat, typed fields."""

    zpid: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zipcode: str | None = None
    price: int | None = None
    currency: str | None = None
    beds: float | None = None
    baths: float | None = None
    area_sqft: int | None = None
    home_type: str | None = None
    status: str | None = None
    zestimate: int | None = None
    days_on_zillow: int | None = None
    broker_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    listing_url: str | None = None
    image_url: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Return the listing as a plain dict (JSON-serializable)."""
        return asdict(self)


def _coerce_price(value: Any) -> tuple[int | None, str | None]:
    """Flatten a ``{"value": ..., "currency": ...}`` price object.

    The parsed_data payload returns prices as an object; some rows carry the
    value as a bare number or string. Return ``(amount, currency)`` and never
    raise on a malformed row.
    """
    if isinstance(value, dict):
        amount = value.get("value")
        currency = value.get("currency")
    else:
        amount, currency = value, None
    if isinstance(amount, str):
        digits = "".join(ch for ch in amount if ch.isdigit())
        amount = int(digits) if digits else None
    elif isinstance(amount, float):
        amount = int(amount)
    elif not isinstance(amount, int):
        amount = None
    return amount, currency


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    return None


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


_KNOWN_FIELDS = {
    "zpid",
    "address",
    "address_city",
    "address_state",
    "address_zipcode",
    "price",
    "price_raw",
    "beds",
    "baths",
    "area_sqft",
    "home_type",
    "status",
    "zestimate",
    "days_on_zillow",
    "broker_name",
    "latitude",
    "longitude",
    "listing_url",
    "image_url",
}


def normalize_item(item: dict[str, Any]) -> Listing:
    """Map one raw parsed_data item onto a :class:`Listing`."""
    price, currency = _coerce_price(item.get("price"))
    if price is None:  # fall back to the un-normalized price if needed
        price, _ = _coerce_price(item.get("price_raw"))
    extra = {k: v for k, v in item.items() if k not in _KNOWN_FIELDS}
    return Listing(
        zpid=str(item["zpid"]) if item.get("zpid") is not None else None,
        address=item.get("address"),
        city=item.get("address_city"),
        state=item.get("address_state"),
        zipcode=item.get("address_zipcode"),
        price=price,
        currency=currency,
        beds=_as_float(item.get("beds")),
        baths=_as_float(item.get("baths")),
        area_sqft=_as_int(item.get("area_sqft")),
        home_type=item.get("home_type"),
        status=item.get("status"),
        zestimate=_as_int(item.get("zestimate")),
        days_on_zillow=_as_int(item.get("days_on_zillow")),
        broker_name=item.get("broker_name"),
        latitude=_as_float(item.get("latitude")),
        longitude=_as_float(item.get("longitude")),
        listing_url=item.get("listing_url"),
        image_url=item.get("image_url"),
        extra=extra,
    )


def location_to_url(location: str) -> str:
    """Turn a human location ("Austin, TX") into a Zillow search URL.

    A value that already looks like an http(s) URL is returned unchanged, so the
    caller can paste a fully-built Zillow search URL (with filters) directly.
    """
    text = location.strip()
    if text.lower().startswith(("http://", "https://")):
        return text
    slug = "-".join(text.replace(",", " ").split())
    return _SEARCH_BASE.format(slug=slug)


def paginate_url(url: str, page: int) -> str:
    """Return the Zillow search URL for ``page`` (1-indexed).

    Zillow encodes pagination as a ``{n}_p/`` path segment, e.g.
    ``.../Austin-TX_rb/2_p/``. Page 1 is the bare URL.
    """
    base = url if url.endswith("/") else url + "/"
    if page <= 1:
        return base
    return f"{base}{page}_p/"


class ZillowScraper:
    """Scrape Zillow "for sale" search results via ScrapeUnblocker.

    Parameters
    ----------
    api_key:
        ScrapeUnblocker API key. If omitted, the SDK reads ``SCRAPEUNBLOCKER_KEY``
        from the environment.
    proxy_country:
        ISO-3166 country to route the request through (default ``"US"`` - Zillow
        only serves US real estate).
    max_retries:
        Number of extra attempts on a transient error before giving up.
    retry_backoff:
        Base seconds for exponential backoff between retries.
    client:
        A pre-built ``scrapeunblocker.Client`` (mainly for testing). When given,
        ``api_key`` is ignored.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        proxy_country: str = "US",
        max_retries: int = 3,
        retry_backoff: float = 1.5,
        client: Client | None = None,
    ) -> None:
        self.proxy_country = proxy_country
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self._sleep = time.sleep
        self.client = client or Client(api_key=api_key)

    def _fetch_page(self, url: str, proxy_country: str) -> list[dict[str, Any]]:
        """Fetch one search page and return its raw item dicts, with retries."""
        attempt = 0
        while True:
            try:
                result = self.client.get_parsed(url, proxy_country=proxy_country)
                break
            except _TRANSIENT_ERRORS:
                attempt += 1
                if attempt > self.max_retries:
                    raise
                self._sleep(self.retry_backoff * (2 ** (attempt - 1)))
        data = getattr(result, "data", None)
        if not isinstance(data, dict):
            return []
        items = data.get("items")
        return items if isinstance(items, list) else []

    def search(
        self,
        location: str,
        *,
        pages: int = 1,
        proxy_country: str | None = None,
    ) -> list[Listing]:
        """Scrape ``pages`` of results for ``location``.

        ``location`` may be a place ("Austin, TX", "90210") or a full Zillow
        search URL. Collection stops early once a page returns no results.
        """
        return list(self.iter_search(location, pages=pages, proxy_country=proxy_country))

    def iter_search(
        self,
        location: str,
        *,
        pages: int = 1,
        proxy_country: str | None = None,
    ) -> Iterator[Listing]:
        """Yield listings one at a time (lazy version of :meth:`search`)."""
        base_url = location_to_url(location)
        country = proxy_country or self.proxy_country
        for page in range(1, max(pages, 1) + 1):
            page_url = paginate_url(base_url, page)
            items = self._fetch_page(page_url, country)
            if not items:
                break
            for item in items:
                yield normalize_item(item)


def filter_listings(
    listings: Iterable[Listing],
    *,
    min_price: int | None = None,
    max_price: int | None = None,
    min_beds: float | None = None,
) -> list[Listing]:
    """Return only the listings matching the given price / bed constraints."""
    out = []
    for home in listings:
        if min_price is not None and (home.price is None or home.price < min_price):
            continue
        if max_price is not None and (home.price is None or home.price > max_price):
            continue
        if min_beds is not None and (home.beds is None or home.beds < min_beds):
            continue
        out.append(home)
    return out


_CSV_COLUMNS = [
    "zpid",
    "address",
    "city",
    "state",
    "zipcode",
    "price",
    "currency",
    "beds",
    "baths",
    "area_sqft",
    "home_type",
    "status",
    "zestimate",
    "days_on_zillow",
    "broker_name",
    "latitude",
    "longitude",
    "listing_url",
]


def listings_to_csv(listings: Iterable[Listing]) -> str:
    """Serialize listings to a CSV string (a stable, flat column subset)."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=_CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for home in listings:
        writer.writerow({col: home.as_dict().get(col) for col in _CSV_COLUMNS})
    return buffer.getvalue()
