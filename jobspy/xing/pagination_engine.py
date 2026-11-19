from __future__ import annotations

from collections.abc import Iterator

from jobspy.xing.exceptions import (
    XingGraphQLError,
    XingPageLoadError,
)
from jobspy.xing.graphql_parser import parse_graphql_results
from jobspy.xing.pagination import (
    GraphQLPageLoader,
    PaginationProgress,
    PaginationState,
    PaginationStopReason,
    ParsedGraphQLPage,
    parse_pagination_info,
)


class GraphQLPaginationEngine:
    """Load and parse XING GraphQL pages using shared pagination rules."""

    def __init__(
        self,
        loader: GraphQLPageLoader,
        *,
        required_results: int,
        page_size: int = 20,
        max_pages: int = 50,
        max_no_progress_pages: int = 3,
        allow_partial: bool = False,
    ) -> None:
        if required_results < 0:
            raise ValueError("required_results cannot be negative")
        if page_size <= 0:
            raise ValueError("page_size must be positive")
        if max_pages <= 0:
            raise ValueError("max_pages must be positive")
        if max_no_progress_pages <= 0:
            raise ValueError("max_no_progress_pages must be positive")

        self.loader = loader
        self.required_results = required_results
        self.max_pages = max_pages
        self.max_no_progress_pages = max_no_progress_pages
        self.allow_partial = allow_partial

        self.state = PaginationState(
            offset=0,
            page_size=page_size,
        )
        self.progress = PaginationProgress()

        self._seen: set[str] = set()
        self._no_progress_pages = 0
        self._started = False

    def __iter__(self) -> Iterator[ParsedGraphQLPage]:
        if self._started:
            raise RuntimeError(
                "GraphQLPaginationEngine instances can only be iterated once"
            )

        self._started = True
        return self._iterate()

    def _handle_failure(
        self,
        message: str,
        exception_type: type[XingPageLoadError] | type[XingGraphQLError],
        cause: Exception,
    ) -> bool:
        """Return True if partial recovery is permitted; otherwise raise."""

        if self.allow_partial and self._seen:
            self.progress.stop_reason = PaginationStopReason.PARTIAL
            self.progress.warnings.append(message)
            return True

        raise exception_type(message) from cause

    def _iterate(self) -> Iterator[ParsedGraphQLPage]:
        if self.required_results == 0:
            self.progress.stop_reason = PaginationStopReason.COMPLETED
            return

        for _ in range(self.max_pages):
            offset = self.state.offset

            try:
                payload = self.loader(
                    offset,
                    self.state.page_size,
                )
            except Exception as exc:
                message = f"XING page loading failed at offset {offset}: {exc}"

                if self._handle_failure(
                    message,
                    XingPageLoadError,
                    exc,
                ):
                    return

            try:
                if not isinstance(payload, dict):
                    raise ValueError("GraphQL payload must be a dictionary")

                if payload.get("errors"):
                    raise ValueError(f"GraphQL errors: {payload['errors']}")

                info = parse_pagination_info(payload)
                jobs = parse_graphql_results(payload)

            except (ValueError, TypeError) as exc:
                message = f"Invalid XING GraphQL response at offset {offset}: {exc}"

                if self._handle_failure(
                    message,
                    XingGraphQLError,
                    exc,
                ):
                    return

            self.progress.pages_fetched += 1
            self.progress.raw_jobs_seen += info.result_count

            new_jobs = []

            for job in jobs:
                key = job.id or job.job_url

                if key in self._seen:
                    continue

                self._seen.add(key)
                new_jobs.append(job)

            if new_jobs:
                self._no_progress_pages = 0
            else:
                self._no_progress_pages += 1

            self.progress.unique_jobs_seen = len(self._seen)

            remaining = self.required_results - self.progress.unique_jobs_seen

            should_continue = self.state.should_continue(
                info,
                remaining_needed=remaining,
            )

            self.state.advance(info)

            if remaining <= 0:
                self.progress.stop_reason = PaginationStopReason.COMPLETED

            elif not should_continue:
                self.progress.stop_reason = PaginationStopReason.EXHAUSTED

            elif self._no_progress_pages >= self.max_no_progress_pages:
                self.progress.stop_reason = PaginationStopReason.NO_PROGRESS
                self.progress.warnings.append(
                    "XING pagination stopped after "
                    f"{self._no_progress_pages} pages without "
                    "new valid jobs"
                )

            yield ParsedGraphQLPage(
                payload=payload,
                jobs=jobs,
                info=info,
                offset=offset,
                new_jobs=new_jobs,
            )

            if self.progress.stop_reason is not None:
                return

        self.progress.stop_reason = PaginationStopReason.MAX_PAGES

        self.progress.warnings.append(
            "XING pagination reached max_pages="
            f"{self.max_pages} before collecting "
            f"{self.required_results} unique jobs"
        )
