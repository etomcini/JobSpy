from __future__ import annotations

from collections.abc import Callable

from jobspy.model import JobPost, ScraperInput
from jobspy.xing.detail import enrich_job_post
from jobspy.xing.exceptions import (
    XingGraphQLError,
    XingPageLoadError,
)
from jobspy.xing.graphql_parser import parse_graphql_results
from jobspy.xing.pagination import (
    GraphQLPageLoader,
    PaginationState,
    parse_pagination_info,
)
from jobspy.xing.search_result import (
    SearchMetrics,
    SearchStatus,
    XingSearchResult,
)


def run_graphql_search(
    scraper_input: ScraperInput,
    loader: GraphQLPageLoader,
    *,
    detail_loader: Callable[[str], str] | None = None,
    page_size: int = 20,
    max_pages: int = 50,
    max_no_progress_pages: int = 3,
    allow_partial: bool = False,
) -> XingSearchResult:
    """Run an offline, injected-loader GraphQL search."""

    if page_size <= 0:
        raise ValueError("page_size must be positive")
    if max_pages <= 0:
        raise ValueError("max_pages must be positive")
    if max_no_progress_pages <= 0:
        raise ValueError("max_no_progress_pages must be positive")

    metrics = SearchMetrics()
    warnings: list[str] = []
    jobs: list[JobPost] = []
    seen: set[str] = set()

    start = scraper_input.offset
    wanted = scraper_input.results_wanted
    required = start + wanted

    if wanted <= 0:
        return XingSearchResult(
            status=SearchStatus.COMPLETED,
            metrics=metrics,
        )

    state = PaginationState(
        offset=0,
        page_size=page_size,
    )

    no_progress_pages = 0
    status = SearchStatus.LIMIT_REACHED

    for _ in range(max_pages):
        try:
            payload = loader(state.offset, state.page_size)
        except Exception as exc:
            if not allow_partial or not jobs:
                raise XingPageLoadError(
                    f"Page loading failed at offset {state.offset}: {exc}"
                ) from exc

            warnings.append(f"Page loading failed at offset {state.offset}: {exc}")
            status = SearchStatus.PARTIAL
            break

        try:
            if not isinstance(payload, dict):
                raise ValueError("Invalid GraphQL payload")

            if payload.get("errors"):
                raise ValueError(f"GraphQL errors: {payload['errors']}")

            info = parse_pagination_info(payload)
            page_jobs = parse_graphql_results(payload)

        except (ValueError, TypeError) as exc:
            if not allow_partial or not jobs:
                raise XingGraphQLError(
                    f"Invalid response at offset {state.offset}: {exc}"
                ) from exc

            warnings.append(f"Invalid response at offset {state.offset}: {exc}")
            status = SearchStatus.PARTIAL
            break

        metrics.pages_fetched += 1
        metrics.raw_jobs_seen += info.result_count

        previous_count = len(seen)

        for job in page_jobs:
            key = job.id or job.job_url

            if key in seen:
                continue

            seen.add(key)
            jobs.append(job)

        metrics.unique_jobs_seen = len(seen)

        remaining = required - len(jobs)

        if remaining <= 0:
            status = SearchStatus.COMPLETED
            break

        if len(seen) == previous_count:
            no_progress_pages += 1
        else:
            no_progress_pages = 0

        should_continue = state.should_continue(
            info,
            remaining_needed=remaining,
        )

        state.advance(info)

        if not should_continue:
            status = SearchStatus.EXHAUSTED
            break

        if no_progress_pages >= max_no_progress_pages:
            warnings.append(
                f"Pagination stopped after {no_progress_pages} pages without new jobs"
            )
            status = SearchStatus.LIMIT_REACHED
            break

    selected = jobs[start:required]

    if scraper_input.fetch_description:
        if detail_loader is None:
            warnings.append("Descriptions requested, but no detail loader was provided")
        else:
            enriched: list[JobPost] = []

            for job in selected:
                try:
                    html = detail_loader(job.job_url)
                    enriched.append(
                        enrich_job_post(
                            job,
                            html,
                            scraper_input.description_format,
                        )
                    )
                except Exception as exc:
                    warnings.append(f"Could not enrich job {job.id}: {exc}")
                    enriched.append(job)

            selected = enriched

    if status == SearchStatus.LIMIT_REACHED:
        warnings.append("Search stopped before reaching the requested number of jobs")

    return XingSearchResult(
        jobs=selected,
        status=status,
        metrics=metrics,
        warnings=warnings,
    )
