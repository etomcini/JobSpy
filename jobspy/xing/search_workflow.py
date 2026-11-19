from __future__ import annotations

from collections.abc import Callable

from jobspy.model import JobPost, ScraperInput
from jobspy.xing.detail import enrich_job_post
from jobspy.xing.pagination import (
    GraphQLPageLoader,
    PaginationStopReason,
)
from jobspy.xing.pagination_engine import GraphQLPaginationEngine
from jobspy.xing.search_result import (
    SearchMetrics,
    SearchStatus,
    XingSearchResult,
)


def _map_stop_reason(
    reason: PaginationStopReason | None,
) -> SearchStatus:
    """Translate internal pagination outcomes to public search statuses."""

    match reason:
        case PaginationStopReason.COMPLETED:
            return SearchStatus.COMPLETED

        case PaginationStopReason.EXHAUSTED:
            return SearchStatus.EXHAUSTED

        case PaginationStopReason.PARTIAL:
            return SearchStatus.PARTIAL

        case PaginationStopReason.MAX_PAGES | PaginationStopReason.NO_PROGRESS:
            return SearchStatus.LIMIT_REACHED

        case _:
            raise RuntimeError(f"Unexpected pagination stop reason: {reason}")


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
    """Run an offline XING GraphQL search using shared pagination."""

    start = scraper_input.offset
    wanted = scraper_input.results_wanted
    required = start + wanted

    # Validate the pagination configuration even for empty searches.
    engine = GraphQLPaginationEngine(
        loader,
        required_results=max(required, 0),
        page_size=page_size,
        max_pages=max_pages,
        max_no_progress_pages=max_no_progress_pages,
        allow_partial=allow_partial,
    )

    if wanted <= 0:
        return XingSearchResult(
            status=SearchStatus.COMPLETED,
            metrics=SearchMetrics(),
        )

    jobs: list[JobPost] = []

    for page in engine:
        jobs.extend(page.new_jobs)

    progress = engine.progress

    metrics = SearchMetrics(
        pages_fetched=progress.pages_fetched,
        raw_jobs_seen=progress.raw_jobs_seen,
        unique_jobs_seen=progress.unique_jobs_seen,
    )

    warnings = list(progress.warnings)
    status = _map_stop_reason(progress.stop_reason)

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
