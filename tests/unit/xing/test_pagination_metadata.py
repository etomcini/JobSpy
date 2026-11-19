from typing import Any

import pytest

from jobspy.xing.pagination import (
    PaginationInfo,
    PaginationState,
    parse_pagination_info,
)


def make_payload(
    result_count: int,
    total: int = -1,
    bounded_total: int | None = None,
    count_type: str = "EXACT",
) -> dict[str, Any]:
    search: dict[str, Any] = {
        "total": total,
        "collection": [{} for _ in range(result_count)],
    }

    if bounded_total is not None:
        search["boundedTotal"] = {
            "total": bounded_total,
            "countType": count_type,
        }

    return {
        "data": {
            "jobSearchByQuery": search,
        }
    }


def test_exact_bounded_total() -> None:
    payload = make_payload(
        result_count=3,
        bounded_total=83,
    )

    info = parse_pagination_info(payload)

    assert info.result_count == 3
    assert info.total == 83
    assert info.total_is_exact is True


def test_negative_total_is_unknown() -> None:
    payload = make_payload(
        result_count=20,
        total=-1,
    )

    info = parse_pagination_info(payload)

    assert info.total is None
    assert info.total_is_exact is False


def test_regular_total() -> None:
    payload = make_payload(
        result_count=20,
        total=100,
    )

    info = parse_pagination_info(payload)

    assert info.total == 100
    assert info.total_is_exact is True


def test_non_exact_bounded_total() -> None:
    payload = make_payload(
        result_count=20,
        bounded_total=1000,
        count_type="LOWER_BOUND",
    )

    info = parse_pagination_info(payload)

    assert info.total == 1000
    assert info.total_is_exact is False


def test_empty_page_stops() -> None:
    state = PaginationState(
        offset=40,
        page_size=20,
    )

    info = PaginationInfo(
        result_count=0,
        total=None,
        total_is_exact=False,
    )

    assert (
        state.should_continue(
            info,
            remaining_needed=10,
        )
        is False
    )


def test_full_page_continues() -> None:
    state = PaginationState(
        offset=20,
        page_size=20,
    )

    info = PaginationInfo(
        result_count=20,
        total=None,
        total_is_exact=False,
    )

    assert (
        state.should_continue(
            info,
            remaining_needed=10,
        )
        is True
    )


def test_exact_total_stops() -> None:
    state = PaginationState(
        offset=80,
        page_size=20,
    )

    info = PaginationInfo(
        result_count=3,
        total=83,
        total_is_exact=True,
    )

    assert (
        state.should_continue(
            info,
            remaining_needed=10,
        )
        is False
    )


def test_partial_page_stops() -> None:
    state = PaginationState(
        offset=40,
        page_size=20,
    )

    info = PaginationInfo(
        result_count=8,
        total=None,
        total_is_exact=False,
    )

    assert (
        state.should_continue(
            info,
            remaining_needed=10,
        )
        is False
    )


def test_requested_limit_stops() -> None:
    state = PaginationState(
        offset=0,
        page_size=20,
    )

    info = PaginationInfo(
        result_count=20,
        total=None,
        total_is_exact=False,
    )

    assert (
        state.should_continue(
            info,
            remaining_needed=0,
        )
        is False
    )


def test_advance_offset() -> None:
    state = PaginationState(
        offset=80,
        page_size=20,
    )

    info = PaginationInfo(
        result_count=3,
        total=83,
        total_is_exact=True,
    )

    state.advance(info)

    assert state.offset == 83


@pytest.mark.parametrize(
    "offset,page_size",
    [
        (-1, 20),
        (0, 0),
        (0, -5),
    ],
)
def test_invalid_pagination_state(
    offset: int,
    page_size: int,
) -> None:
    with pytest.raises(ValueError):
        PaginationState(
            offset=offset,
            page_size=page_size,
        )


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"data": None},
        {"data": {}},
        {"data": {"jobSearchByQuery": None}},
        {"data": {"jobSearchByQuery": {"collection": None}}},
    ],
)
def test_invalid_payload(
    payload: dict[str, Any],
) -> None:
    with pytest.raises(ValueError):
        parse_pagination_info(payload)
