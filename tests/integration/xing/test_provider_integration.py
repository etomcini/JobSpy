from __future__ import annotations

from unittest.mock import patch

import pandas as pd

from jobspy import scrape_jobs
from jobspy.model import JobPost, ScraperInput, Site
from jobspy.xing import Xing


def make_job() -> JobPost:
    return JobPost(
        id="xing-1001",
        site="xing",
        job_url="https://www.xing.com/jobs/python-developer-1001",
        title="Python Developer",
        company="Example Company",
    )


def test_xing_registered_in_scraper_mapping() -> None:
    from jobspy import SCRAPER_MAPPING

    assert Site.XING in SCRAPER_MAPPING
    assert SCRAPER_MAPPING[Site.XING] is Xing


def test_scrape_jobs_invokes_xing_provider() -> None:
    with patch.object(
        Xing,
        "scrape",
        return_value=[make_job()],
    ) as mock_scrape:
        result = scrape_jobs(
            site_name=["xing"],
            search_term="Python Developer",
            location="Berlin",
            results_wanted=1,
            verbose=0,
        )

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1

    row = result.iloc[0]

    assert row["site"] == "xing"
    assert row["id"] == "xing-1001"
    assert row["title"] == "Python Developer"
    assert row["company"] == "Example Company"

    mock_scrape.assert_called_once()

    scraper_input = mock_scrape.call_args.args[0]

    assert isinstance(scraper_input, ScraperInput)
    assert scraper_input.search_term == "Python Developer"
    assert scraper_input.location == "Berlin"
    assert scraper_input.results_wanted == 1


def test_xing_empty_results_preserve_dataframe_schema() -> None:
    with patch.object(Xing, "scrape", return_value=[]):
        result = scrape_jobs(
            site_name=["xing"],
            search_term="Python Developer",
            verbose=0,
        )

    assert result.empty
    assert list(result.columns) == list(JobPost.model_fields)


def test_xing_reports_missing_page_loader() -> None:
    result = scrape_jobs(
        site_name=["xing"],
        search_term="Python Developer",
        verbose=0,
    )

    assert result.empty
    assert "xing" in result.attrs["errors"]

    error = result.attrs["errors"]["xing"]

    assert "no permitted page loader is configured" in error.lower()
