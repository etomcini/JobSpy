from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from jobspy.model import JobPost

GraphQLPayload = dict[str, Any]
GraphQLPageLoader = Callable[[int, int], GraphQLPayload]
WarningCallback = Callable[[str], None]


@dataclass(frozen=True)
class ParsedGraphQLPage:
    """One validated and parsed GraphQL search page."""

    payload: GraphQLPayload
    jobs: list[JobPost]
    info: PaginationInfo
    offset: int
    new_jobs: list[JobPost]


@dataclass
class PaginationProgress:
    """Metrics and final state of a pagination run."""

    pages_fetched: int = 0
    raw_jobs_seen: int = 0
    unique_jobs_seen: int = 0
    stop_reason: PaginationStopReason | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PaginationInfo:
    """Metadata from one XING GraphQL search response."""

    result_count: int
    total: int | None
    total_is_exact: bool


class PaginationStopReason(StrEnum):
    """Reason why GraphQL pagination stopped."""

    COMPLETED = "completed"
    EXHAUSTED = "exhausted"
    PARTIAL = "partial"
    MAX_PAGES = "max_pages"
    NO_PROGRESS = "no_progress"


def parse_pagination_info(
    payload: dict[str, Any],
) -> PaginationInfo:
    """Extract pagination metadata from a GraphQL response."""

    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("Missing GraphQL data")

    search = data.get("jobSearchByQuery")
    if not isinstance(search, dict):
        raise ValueError("Missing jobSearchByQuery")

    collection = search.get("collection")
    if not isinstance(collection, list):
        raise ValueError("Invalid job collection")

    bounded = search.get("boundedTotal")

    total: int | None = None
    total_is_exact = False

    if isinstance(bounded, dict):
        bounded_total = bounded.get("total")
        count_type = bounded.get("countType")

        if (
            isinstance(bounded_total, int)
            and not isinstance(bounded_total, bool)
            and bounded_total >= 0
        ):
            total = bounded_total
            total_is_exact = count_type == "EXACT"

    if total is None:
        raw_total = search.get("total")

        if (
            isinstance(raw_total, int)
            and not isinstance(raw_total, bool)
            and raw_total >= 0
        ):
            total = raw_total
            total_is_exact = True

    return PaginationInfo(
        result_count=len(collection),
        total=total,
        total_is_exact=total_is_exact,
    )


@dataclass
class PaginationState:
    """Track offset-based pagination progress."""

    offset: int = 0
    page_size: int = 20

    def __post_init__(self) -> None:
        if self.offset < 0:
            raise ValueError("offset cannot be negative")

        if self.page_size <= 0:
            raise ValueError("page_size must be positive")

    def should_continue(
        self,
        info: PaginationInfo,
        remaining_needed: int,
    ) -> bool:
        """Determine whether another page is needed."""

        if remaining_needed <= 0:
            return False

        if info.result_count == 0:
            return False

        next_offset = self.offset + info.result_count

        if info.total_is_exact and info.total is not None and next_offset >= info.total:
            return False

        # A partial page usually indicates the end of results.
        if info.result_count < self.page_size:
            return False

        return True

    def advance(self, info: PaginationInfo) -> None:
        """Advance the offset after processing a page."""

        self.offset += info.result_count


def iter_graphql_pages(
    loader: GraphQLPageLoader,
    *,
    required_results: int,
    page_size: int = 20,
    max_pages: int = 50,
    max_no_progress_pages: int = 3,
    allow_partial: bool = False,
    on_warning: WarningCallback | None = None,
) -> Iterator[GraphQLPayload]:
    """Yield raw GraphQL payloads using the shared pagination engine."""

    from jobspy.xing.pagination_engine import GraphQLPaginationEngine

    engine = GraphQLPaginationEngine(
        loader,
        required_results=required_results,
        page_size=page_size,
        max_pages=max_pages,
        max_no_progress_pages=max_no_progress_pages,
        allow_partial=allow_partial,
    )

    for page in engine:
        yield page.payload

    if on_warning is not None:
        for warning in engine.progress.warnings:
            on_warning(warning)
