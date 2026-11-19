import json
from pathlib import Path
from unittest.mock import Mock

from jobspy.model import ScraperInput
from jobspy.xing import Xing
from jobspy.xing.pagination import PaginationStopReason
from jobspy.xing.pagination_engine import GraphQLPaginationEngine
from jobspy.xing.search_result import SearchStatus

FIXTURE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "xing" / "graphql_page_last.json"
)


def load_payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_search_uses_shared_engine() -> None:
    payload = load_payload()

    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=3,
    )

    result = Xing().search_with_metadata(
        scraper_input,
        Mock(return_value=payload),
        page_size=20,
    )

    assert result.status == SearchStatus.COMPLETED
    assert result.count == 3
    assert result.metrics.pages_fetched == 1


def test_engine_exposes_completion_reason() -> None:
    payload = load_payload()

    engine = GraphQLPaginationEngine(
        Mock(return_value=payload),
        required_results=3,
    )

    pages = list(engine)

    assert len(pages) == 1
    assert engine.progress.stop_reason == PaginationStopReason.COMPLETED


def test_search_preserves_metrics() -> None:
    payload = load_payload()

    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=3,
    )

    result = Xing().search_with_metadata(
        scraper_input,
        Mock(return_value=payload),
    )

    assert result.metrics.pages_fetched == 1
    assert result.metrics.raw_jobs_seen == 3
    assert result.metrics.unique_jobs_seen == 3
