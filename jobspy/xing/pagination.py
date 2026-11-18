from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
