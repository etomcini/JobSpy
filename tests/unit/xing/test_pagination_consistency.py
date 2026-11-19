from typing import Any
from unittest.mock import Mock

from jobspy.model import ScraperInput
from jobspy.xing import Xing
from jobspy.xing.graphql_parser import parse_graphql_results
from jobspy.xing.page_loader import iter_graphql_pages


def make_payload(numbers: list[int]) -> dict[str, Any]:
    return {
        "data": {
            "jobSearchByQuery": {
                "total": -1,
                "collection": [
                    {
                        "jobDetail": {
                            "id": f"{number}.abc",
                            "url": (f"https://www.xing.com/jobs/test-job-{number}"),
                            "title": f"Job {number}",
                            "companyInfo": {
                                "companyNameOverride": "Test Company",
                            },
                        }
                    }
                    for number in numbers
                ],
            }
        }
    }


def test_both_pagination_paths_collect_same_jobs() -> None:
    pages = [
        make_payload([1, 2]),
        make_payload([2, 3]),
        make_payload([4, 5]),
    ]

    scraper_input = ScraperInput(
        site_name=["xing"],
        results_wanted=5,
    )

    old_pages = list(
        iter_graphql_pages(
            Mock(side_effect=pages),
            required_results=5,
            page_size=2,
        )
    )

    old_jobs = []
    seen = set()

    for payload in old_pages:
        for job in parse_graphql_results(payload):
            if job.id not in seen:
                seen.add(job.id)
                old_jobs.append(job)

    result = Xing().search_with_metadata(
        scraper_input,
        Mock(side_effect=pages),
        page_size=2,
    )

    assert [job.id for job in old_jobs] == [job.id for job in result.jobs]
    assert result.metrics.unique_jobs_seen == 5
