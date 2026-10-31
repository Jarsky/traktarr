import datetime as dt
import logging

import pytest

from helpers import misc as misc_helper
from helpers import parameter
from helpers.trakt import blacklisted_release_date
from misc.log import ConsoleFormatter

TODAY = dt.date(2026, 11, 1)


@pytest.mark.parametrize("spec, want", [
    ("-3mo", "2026-08-01"), ("+12mo", "2027-11-01"), ("-90d", "2026-08-03"), ("-2w", "2026-10-18"),
    ("+1y", "2027-11-01"), ("-3 months", "2026-08-01"), ("today", "2026-11-01"), ("2026-06-15", "2026-06-15"),
])
def test_resolve_date(spec, want):
    assert misc_helper.resolve_date(spec, TODAY).isoformat() == want


def test_resolve_date_empty_and_month_end():
    assert misc_helper.resolve_date("", TODAY) is None
    assert misc_helper.resolve_date(None, TODAY) is None
    assert misc_helper.resolve_date("-1mo", dt.date(2026, 3, 31)).isoformat() == "2026-02-28"


def test_resolve_date_rejects_nonsense():
    with pytest.raises(ValueError):
        misc_helper.resolve_date("3 months ago", TODAY)


@pytest.mark.parametrize("spec, offset", [("{year}", 0), ("{year}+1", 1), ("{year}-2", -2), (0, 0), ("+1", 1)])
def test_relative_years(spec, offset):
    _, earliest, _ = parameter.years(None, spec, spec)
    assert earliest == dt.date.today().year + offset


def test_fixed_years():
    assert parameter.years(None, 2025, 2027)[1:] == (2025, 2027)


def test_release_date_filter():
    movie = {"movie": {"title": "X", "released": "2026-07-01"}}
    show = {"show": {"title": "Y", "first_aired": "2025-12-01T00:00:00.000Z"}}
    assert blacklisted_release_date(movie, "movie", None, None) is False
    assert blacklisted_release_date(movie, "movie", "2026-06-01", "2026-12-31") is False
    assert blacklisted_release_date(movie, "movie", "2026-08-01", None) is True
    assert blacklisted_release_date(show, "show", "2026-01-01", None) is True
    assert blacklisted_release_date({"movie": {"title": "Z", "released": None}}, "movie", "-3mo", None) is True


def test_allowed_genres_needs_one_match():
    item = lambda *g: {"movie": {"genres": list(g)}}
    allowed = ["science-fiction", "horror"]
    assert misc_helper.allowed_genres(allowed, "movie", item("drama", "science-fiction"))
    assert not misc_helper.allowed_genres(allowed, "movie", item("drama"))


def test_anticipated_ranking(monkeypatch):
    import traktarr
    monkeypatch.setattr(traktarr, "log", logging.getLogger("test"))   # set by the CLI at start-up
    items = [{"list_count": n, "movie": {"title": str(n)}} for n in (300, 76000, 5200, 1200)]
    ranked = traktarr.anticipated_by_lists(items, "movies", 5000)
    assert [i["list_count"] for i in ranked] == [76000, 5200]


def test_unreleased():
    import traktarr
    assert traktarr.is_unreleased({"movie": {"released": None}})
    assert traktarr.is_unreleased({"movie": {"released": "2999-01-01"}})
    assert not traktarr.is_unreleased({"movie": {"released": "2001-01-01"}})


def test_console_formatter():
    record = logging.LogRecord("t", logging.INFO, "", 0, "ADDED: 'Dune: Part Three (2026)'", None, None)
    assert ConsoleFormatter(False).format(record).endswith("INFO  ADDED: 'Dune: Part Three (2026)'")
    coloured = ConsoleFormatter(True).format(record)
    assert "\x1b[" in coloured and "Dune: Part Three (2026)" in coloured
