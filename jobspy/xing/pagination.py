from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

from jobspy.xing.exceptions import (
    XingGraphQLError,
    XingPageLoadError,
)
from jobspy.xing.graphql_parser import parse_graphql_results

GraphQLPayload = dict[str, Any]
GraphQLPageLoader = Callable[[int, int], GraphQLPayload]
WarningCallback = Callable[[str], None]


@dataclass(frozen=True)
class PaginationInfo:
    """Metadata from one XING GraphQL search response."""

    result_count: int
    total: int | None
    total_is_exact: bool


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
    """Yield GraphQL pages until enough unique jobs are collected."""

    if required_results < 0:
        raise ValueError("required_results cannot be negative")

    if page_size <= 0:
        raise ValueError("page_size must be positive")

    if max_pages <= 0:
        raise ValueError("max_pages must be positive")

    if max_no_progress_pages <= 0:
        raise ValueError("max_no_progress_pages must be positive")

    if required_results == 0:
        return

    state = PaginationState(
        offset=0,
        page_size=page_size,
    )

    seen: set[str] = set()
    no_progress_pages = 0

    def warn(message: str) -> None:
        if on_warning is not None:
            on_warning(message)

    for _ in range(max_pages):
        try:
            payload = loader(state.offset, state.page_size)
        except Exception as exc:
            message = f"XING page loading failed at offset {state.offset}: {exc}"

            if allow_partial and seen:
                warn(message)
                return

            raise XingPageLoadError(message) from exc

        try:
            if not isinstance(payload, dict):
                raise ValueError("GraphQL payload must be a dictionary")

            if payload.get("errors"):
                raise ValueError(f"GraphQL errors: {payload['errors']}")

            info = parse_pagination_info(payload)
            jobs = parse_graphql_results(payload)

        except (ValueError, TypeError) as exc:
            message = f"Invalid XING GraphQL response at offset {state.offset}: {exc}"

            if allow_partial and seen:
                warn(message)
                return

            raise XingGraphQLError(message) from exc

        previous_count = len(seen)

        for job in jobs:
            key = job.id or job.job_url
            seen.add(key)

        if len(seen) == previous_count:
            no_progress_pages += 1
        else:
            no_progress_pages = 0

        remaining = required_results - len(seen)

        yield payload

        should_continue = state.should_continue(
            info,
            remaining_needed=remaining,
        )

        state.advance(info)

        if not should_continue:
            return

        if no_progress_pages >= max_no_progress_pages:
            warn(
                "XING pagination stopped after "
                f"{no_progress_pages} pages without "
                "new valid jobs"
            )
            return

    if len(seen) < required_results:
        warn(
            "XING pagination reached max_pages="
            f"{max_pages} before collecting "
            f"{required_results} unique jobs"
        )
