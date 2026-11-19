from unittest.mock import patch

from jobspy import SCRAPER_MAPPING, scrape_jobs
from jobspy.model import Scraper, ScraperInput, Site
from jobspy.xing import Xing


def test_xing_is_registered():
    assert Site.XING in SCRAPER_MAPPING
    assert SCRAPER_MAPPING[Site.XING] is Xing


def test_xing_inherits_scraper():
    assert issubclass(Xing, Scraper)


def test_xing_is_not_enabled_by_default():
    scraper_input = ScraperInput()

    assert Site.XING not in scraper_input.site_name


def test_xing_accepts_search_input():
    scraper_input = ScraperInput(
        site_name=[Site.XING],
        search_term="Python Developer",
        location="Berlin",
        results_wanted=10,
    )

    assert scraper_input.site_name == [Site.XING]
    assert scraper_input.search_term == "Python Developer"
    assert scraper_input.location == "Berlin"


def test_xing_public_api_uses_html_fallback() -> None:
    with (
        patch.object(Xing, "page_loader_factory", None),
        patch.object(
            Xing,
            "_scrape_html",
            return_value=[],
        ) as mock_html,
    ):
        jobs = scrape_jobs(
            site_name="xing",
            search_term="Python Developer",
            location="Berlin",
            results_wanted=5,
            verbose=0,
        )

    assert jobs.empty
    mock_html.assert_called_once()
