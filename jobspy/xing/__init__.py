from __future__ import annotations

from jobspy.model import JobPost, Scraper, ScraperInput


class Xing(Scraper):
    """XING job scraper.

    Currently provides integration with JobSpy's scraper
    architecture. HTTP scraping will be implemented later.
    """

    def scrape(
        self,
        scraper_input: ScraperInput,
    ) -> list[JobPost]:
        self.fail("XING scraping is not implemented yet")
        return []
