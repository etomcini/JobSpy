from jobspy.xing.pagination import (
    PaginationInfo,
    PaginationProgress,
    PaginationStopReason,
    ParsedGraphQLPage,
)


def test_stop_reason_values() -> None:
    assert PaginationStopReason.COMPLETED == "completed"
    assert PaginationStopReason.EXHAUSTED == "exhausted"
    assert PaginationStopReason.PARTIAL == "partial"
    assert PaginationStopReason.MAX_PAGES == "max_pages"
    assert PaginationStopReason.NO_PROGRESS == "no_progress"


def test_pagination_progress_defaults() -> None:
    progress = PaginationProgress()

    assert progress.pages_fetched == 0
    assert progress.raw_jobs_seen == 0
    assert progress.unique_jobs_seen == 0
    assert progress.stop_reason is None
    assert progress.warnings == []


def test_pagination_progress_warnings_are_independent() -> None:
    first = PaginationProgress()
    second = PaginationProgress()

    first.warnings.append("First search warning")

    assert first.warnings == ["First search warning"]
    assert second.warnings == []


def test_parsed_graphql_page() -> None:
    payload = {
        "data": {
            "jobSearchByQuery": {
                "collection": [],
            }
        }
    }

    info = PaginationInfo(
        result_count=0,
        total=0,
        total_is_exact=True,
    )

    page = ParsedGraphQLPage(
        payload=payload,
        jobs=[],
        info=info,
        offset=20,
        new_jobs=[],
    )

    assert page.payload is payload
    assert page.jobs == []
    assert page.info == info
    assert page.offset == 20
    assert page.new_jobs == []
