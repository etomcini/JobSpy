import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from jobspy.xing.exceptions import XingPageLoadError
from jobspy.xing.pagination import PaginationStopReason
from jobspy.xing.pagination_engine import GraphQLPaginationEngine

FIXTURE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "xing" / "graphql_page_last.json"
)


@pytest.fixture
def graphql_payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_engine_collects_jobs(graphql_payload: dict) -> None:
    loader = Mock(return_value=graphql_payload)

    engine = GraphQLPaginationEngine(
        loader,
        required_results=3,
        page_size=20,
    )

    pages = list(engine)

    assert len(pages) == 1
    assert len(pages[0].new_jobs) == 3
    assert engine.progress.pages_fetched == 1
    assert engine.progress.unique_jobs_seen == 3
    assert engine.progress.stop_reason == PaginationStopReason.COMPLETED


def test_engine_exhausts_results(graphql_payload: dict) -> None:
    engine = GraphQLPaginationEngine(
        Mock(return_value=graphql_payload),
        required_results=100,
        page_size=20,
    )

    pages = list(engine)

    assert len(pages) == 1
    assert engine.progress.stop_reason == PaginationStopReason.EXHAUSTED


def test_engine_deduplicates_jobs(graphql_payload: dict) -> None:
    from copy import deepcopy

    payload = deepcopy(graphql_payload)
    search = payload["data"]["jobSearchByQuery"]

    search.pop("boundedTotal", None)
    search["total"] = 6

    engine = GraphQLPaginationEngine(
        Mock(return_value=payload),
        required_results=10,
        page_size=3,
        max_no_progress_pages=2,
    )

    pages = list(engine)

    assert len(pages) == 2
    assert len(pages[0].new_jobs) == 3
    assert pages[1].new_jobs == []
    assert engine.progress.unique_jobs_seen == 3
    assert engine.progress.stop_reason == PaginationStopReason.EXHAUSTED


def test_engine_recovers_partial_results(graphql_payload: dict) -> None:
    loader = Mock(
        side_effect=[
            graphql_payload,
            RuntimeError("Network unavailable"),
        ]
    )

    engine = GraphQLPaginationEngine(
        loader,
        required_results=10,
        page_size=3,
        allow_partial=True,
    )

    pages = list(engine)

    assert len(pages) == 1
    assert engine.progress.stop_reason == PaginationStopReason.PARTIAL
    assert engine.progress.warnings


def test_engine_raises_without_partial_recovery(
    graphql_payload: dict,
) -> None:
    loader = Mock(
        side_effect=[
            graphql_payload,
            RuntimeError("Network unavailable"),
        ]
    )

    engine = GraphQLPaginationEngine(
        loader,
        required_results=10,
        page_size=3,
    )

    with pytest.raises(XingPageLoadError):
        list(engine)


def test_engine_zero_results_makes_no_requests() -> None:
    loader = Mock()

    engine = GraphQLPaginationEngine(
        loader,
        required_results=0,
    )

    assert list(engine) == []
    assert engine.progress.stop_reason == PaginationStopReason.COMPLETED
    loader.assert_not_called()


def test_engine_is_single_use() -> None:
    engine = GraphQLPaginationEngine(
        Mock(),
        required_results=0,
    )

    assert list(engine) == []

    with pytest.raises(RuntimeError, match="only be iterated once"):
        list(engine)
