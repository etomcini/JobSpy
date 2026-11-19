from jobspy.model import JobPost, Scraper, ScraperInput
from jobspy.xing import Xing
from jobspy.xing.search_result import XingSearchResult


def test_xing_inherits_scraper() -> None:
    assert issubclass(Xing, Scraper)


def test_public_search_methods_exist() -> None:
    assert callable(Xing.process_results)
    assert callable(Xing.process_pages)
    assert callable(Xing.process_graphql_pages)
    assert callable(Xing.process_graphql_search)
    assert callable(Xing.search_with_metadata)


def test_scrape_returns_job_list_annotation() -> None:
    annotations = Xing.scrape.__annotations__

    assert annotations["return"] in (
        "list[JobPost]",
        list[JobPost],
    )


def test_structured_search_result_has_jobs() -> None:
    result = XingSearchResult()

    assert isinstance(result.jobs, list)
    assert result.count == 0


def test_search_input_accepts_xing() -> None:
    scraper_input = ScraperInput(
        site_name=["xing"],
        search_term="Python Developer",
        location="Berlin",
        results_wanted=10,
    )

    assert scraper_input.site_name
    assert scraper_input.results_wanted == 10
