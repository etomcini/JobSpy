from __future__ import annotations

import pytest

from jobspy.model import ScraperInput
from jobspy.xing.config import XingSearchConfig


def make_input(
    *,
    search_term: str | None = "Python Developer",
    location: str | None = "Berlin",
) -> ScraperInput:
    return ScraperInput(
        site_name=["xing"],
        search_term=search_term,
        location=location,
    )


def test_config_from_scraper_input() -> None:
    config = XingSearchConfig.from_scraper_input(make_input())

    assert config.keywords == "Python Developer"
    assert config.location == "Berlin"
    assert config.is_remote is False
    assert config.job_type is None


def test_search_terms_are_normalized() -> None:
    config = XingSearchConfig.from_scraper_input(
        make_input(
            search_term="  Python Developer  ",
            location="  Berlin  ",
        )
    )

    assert config.keywords == "Python Developer"
    assert config.location == "Berlin"


def test_empty_location_becomes_none() -> None:
    config = XingSearchConfig.from_scraper_input(make_input(location="   "))

    assert config.location is None


@pytest.mark.parametrize(
    "search_term",
    [
        None,
        "",
        "   ",
    ],
)
def test_empty_keywords_are_rejected(
    search_term: str | None,
) -> None:
    with pytest.raises(
        ValueError,
        match="XING search keywords are required",
    ):
        XingSearchConfig.from_scraper_input(make_input(search_term=search_term))


def test_remote_filter_is_preserved() -> None:
    scraper_input = ScraperInput(
        site_name=["xing"],
        search_term="Python Developer",
        is_remote=True,
    )

    config = XingSearchConfig.from_scraper_input(scraper_input)

    assert config.is_remote is True


def test_configuration_is_immutable() -> None:
    from dataclasses import FrozenInstanceError

    config = XingSearchConfig.from_scraper_input(make_input())

    with pytest.raises(FrozenInstanceError):
        config.keywords = "Java Developer"
