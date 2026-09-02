"""Tests for the argparse CLI and its wiring (SDK still mocked)."""

from __future__ import annotations

import json

import pytest

from zillow_scraper import cli
from zillow_scraper.scraper import Listing


def test_parser_defaults():
    args = cli.build_parser().parse_args(["Austin, TX"])
    assert args.location == "Austin, TX"
    assert args.pages == 1
    assert args.format == "json"
    assert args.country == "US"


def test_parser_flags():
    args = cli.build_parser().parse_args(
        ["90210", "-p", "3", "-f", "csv", "--min-price", "500000", "--min-beds", "2"]
    )
    assert args.pages == 3
    assert args.format == "csv"
    assert args.min_price == 500000
    assert args.min_beds == 2.0


def test_parser_rejects_bad_format():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["Austin", "-f", "xml"])


def _patch_scraper(monkeypatch, listings):
    class StubScraper:
        def __init__(self, *a, **k):
            pass

        def search(self, location, *, pages=1, proxy_country=None):
            return list(listings)

    monkeypatch.setattr(cli, "ZillowScraper", StubScraper)


def test_main_json_output(monkeypatch, capsys):
    _patch_scraper(monkeypatch, [Listing(zpid="1", address="1 A St", price=100)])
    rc = cli.main(["Austin, TX"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["zpid"] == "1"
    assert payload[0]["price"] == 100


def test_main_csv_to_file(monkeypatch, tmp_path):
    _patch_scraper(monkeypatch, [Listing(zpid="1", city="Austin", price=100)])
    out = tmp_path / "out.csv"
    rc = cli.main(["Austin, TX", "-f", "csv", "-o", str(out)])
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert text.startswith("zpid,address,city")
    assert "Austin" in text


def test_main_applies_price_filter(monkeypatch, capsys):
    _patch_scraper(
        monkeypatch,
        [Listing(zpid="cheap", price=100), Listing(zpid="pricey", price=10_000)],
    )
    cli.main(["Austin, TX", "--max-price", "500"])
    payload = json.loads(capsys.readouterr().out)
    assert [row["zpid"] for row in payload] == ["cheap"]
