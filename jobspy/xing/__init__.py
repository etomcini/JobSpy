from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, ClassVar
from urllib.parse import urlencode

from requests import Session

from jobspy.model import JobPost, Scraper, ScraperInput
from jobspy.xing.client import XingClient
from jobspy.xing.config import XingSearchConfig
from jobspy.xing.detail import enrich_job_post
from jobspy.xing.graphql_parser import parse_graphql_results
from jobspy.xing.page_loader import GraphQLPageLoader
from jobspy.xing.search_result import XingSearchResult
from jobspy.xing.search_workflow import run_graphql_search
from jobspy.xing.util import parse_search_results


class Xing(Scraper):
    """XING job scraper orchestration."""

    def __init__(
        self,
        page_loader_factory: (
            Callable[[XingSearchConfig], GraphQLPageLoader] | None
        ) = None,
    ) -> None:
        super().__init__()
        self._page_loader_factory = page_loader_factory

    page_loader_factory: ClassVar[
        Callable[[XingSearchConfig], GraphQLPageLoader] | None
    ] = None

    def _scrape_html(
        self,
        scraper_input: ScraperInput,
        config: XingSearchConfig,
    ) -> list[JobPost]:
        """Retrieve and parse public XING HTML job listings."""

        params = {"keywords": config.keywords}

        if config.location:
            params["location"] = config.location

        search_url = "https://www.xing.com/jobs/search/ki?" + urlencode(params)

        with Session() as session:
            session.headers.update(
                {
                    "User-Agent": "JobSpy-XING-Integration-Test/0.1",
                    "Accept": "text/html",
                }
            )

            client = XingClient(session)

            search_html = client.get_html(search_url)

            detail_loader = client.get_html if scraper_input.fetch_description else None

            return self.process_results(
                scraper_input,
                search_html,
                detail_loader=detail_loader,
            )

    def process_results(
        self,
        scraper_input: ScraperInput,
        search_html: str,
        detail_loader: Callable[[str], str] | None = None,
    ) -> list[JobPost]:
        """Process one HTML search-result document."""

        return self.process_pages(
            scraper_input,
            [search_html],
            detail_loader=detail_loader,
        )

    def process_pages(
        self,
        scraper_input: ScraperInput,
        pages: Iterable[str],
        detail_loader: Callable[[str], str] | None = None,
    ) -> list[JobPost]:
        """Process HTML search-result pages."""

        parsed_pages = (parse_search_results(html) for html in pages)

        return self._process_job_pages(
            scraper_input,
            parsed_pages,
            detail_loader,
        )

    def process_graphql_pages(
        self,
        scraper_input: ScraperInput,
        pages: Iterable[dict[str, Any]],
        detail_loader: Callable[[str], str] | None = None,
    ) -> list[JobPost]:
        """Process GraphQL search-result pages."""

        parsed_pages = (parse_graphql_results(payload) for payload in pages)

        return self._process_job_pages(
            scraper_input,
            parsed_pages,
            detail_loader,
        )

    def _process_job_pages(
        self,
        scraper_input: ScraperInput,
        pages: Iterable[list[JobPost]],
        detail_loader: Callable[[str], str] | None = None,
    ) -> list[JobPost]:
        """Deduplicate, limit, and optionally enrich parsed jobs."""

        start = scraper_input.offset
        wanted = scraper_input.results_wanted
        required = start + wanted

        if wanted <= 0:
            return []

        jobs: list[JobPost] = []
        seen: set[str] = set()

        for page_jobs in pages:
            for job in page_jobs:
                key = job.id or job.job_url

                if key in seen:
                    continue

                seen.add(key)
                jobs.append(job)

                if len(jobs) >= required:
                    break

            if len(jobs) >= required:
                break

        selected_jobs = jobs[start:required]

        if not scraper_input.fetch_description:
            return selected_jobs

        if detail_loader is None:
            self.warn("XING descriptions requested, but no detail loader was provided")
            return selected_jobs

        return self._enrich_jobs(
            selected_jobs,
            scraper_input,
            detail_loader,
        )

    def _enrich_jobs(
        self,
        jobs: list[JobPost],
        scraper_input: ScraperInput,
        detail_loader: Callable[[str], str],
    ) -> list[JobPost]:
        """Enrich selected jobs, preserving jobs on failure."""

        enriched_jobs: list[JobPost] = []

        for job in jobs:
            try:
                detail_html = detail_loader(job.job_url)

                enriched_job = enrich_job_post(
                    job,
                    detail_html,
                    scraper_input.description_format,
                )

                enriched_jobs.append(enriched_job)

            except Exception as exc:
                self.warn(f"Could not enrich XING job {job.id}: {exc}")
                enriched_jobs.append(job)

        return enriched_jobs

    def scrape(
        self,
        scraper_input: ScraperInput,
    ) -> list[JobPost]:
        """Run XING search using GraphQL or public HTML."""

        try:
            config = XingSearchConfig.from_scraper_input(scraper_input)

            loader_factory = self._page_loader_factory

            if loader_factory is None:
                loader_factory = type(self).page_loader_factory

            if loader_factory is not None:
                page_loader = loader_factory(config)

                return self.process_graphql_search(
                    scraper_input,
                    page_loader,
                )

            # Default: use public HTML search.
            if scraper_input.is_remote:
                self.warn(
                    "XING remote search filtering is not "
                    "implemented; ignoring is_remote"
                )

            if scraper_input.job_type is not None:
                self.warn(
                    "XING job type search filtering is not "
                    "implemented; ignoring job_type"
                )

            if scraper_input.hours_old is not None:
                self.warn(
                    "XING publication-time filtering is not "
                    "implemented; ignoring hours_old"
                )

            return self._scrape_html(
                scraper_input,
                config,
            )

        except Exception as exc:
            self.fail(f"XING search failed: {exc}")
            return []

    def process_graphql_search(
        self,
        scraper_input: ScraperInput,
        page_loader: GraphQLPageLoader,
        detail_loader: Callable[[str], str] | None = None,
        *,
        page_size: int = 20,
        max_pages: int = 50,
        max_no_progress_pages: int = 3,
        allow_partial: bool = False,
    ) -> list[JobPost]:
        """Search GraphQL pages and return jobs without metadata."""

        result = self.search_with_metadata(
            scraper_input,
            page_loader,
            detail_loader=detail_loader,
            page_size=page_size,
            max_pages=max_pages,
            max_no_progress_pages=max_no_progress_pages,
            allow_partial=allow_partial,
        )

        return result.jobs

    def search_with_metadata(
        self,
        scraper_input: ScraperInput,
        page_loader: GraphQLPageLoader,
        detail_loader: Callable[[str], str] | None = None,
        *,
        page_size: int = 20,
        max_pages: int = 50,
        max_no_progress_pages: int = 3,
        allow_partial: bool = False,
    ) -> XingSearchResult:
        """Return jobs together with pagination diagnostics."""

        result = run_graphql_search(
            scraper_input,
            page_loader,
            detail_loader=detail_loader,
            page_size=page_size,
            max_pages=max_pages,
            max_no_progress_pages=max_no_progress_pages,
            allow_partial=allow_partial,
        )

        for warning in result.warnings:
            self.warn(warning)

        return result
