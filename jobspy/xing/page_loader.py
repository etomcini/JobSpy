from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

from jobspy.xing.exceptions import (
    XingGraphQLError,
    XingPageLoadError,
)
from jobspy.xing.graphql_parser import parse_graphql_results
from jobspy.xing.pagination import (
    PaginationState,
    parse_pagination_info,
)

GraphQLPayload = dict[str, Any]
GraphQLPageLoader = Callable[[int, int], GraphQLPayload]
WarningCallback = Callable[[str], None]


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
