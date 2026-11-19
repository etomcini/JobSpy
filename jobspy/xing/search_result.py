from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from jobspy.model import JobPost


class SearchStatus(str, Enum):
    COMPLETED = "completed"
    EXHAUSTED = "exhausted"
    PARTIAL = "partial"
    LIMIT_REACHED = "limit_reached"


@dataclass
class SearchMetrics:
    pages_fetched: int = 0
    raw_jobs_seen: int = 0
    unique_jobs_seen: int = 0


@dataclass
class XingSearchResult:
    jobs: list[JobPost] = field(default_factory=list)
    status: SearchStatus = SearchStatus.COMPLETED
    metrics: SearchMetrics = field(default_factory=SearchMetrics)
    warnings: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.jobs)
