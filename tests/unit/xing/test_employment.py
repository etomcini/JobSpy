import pytest

from jobspy.model import JobType
from jobspy.xing.util import (
    parse_job_types,
    parse_remote_location,
)


@pytest.mark.parametrize(
    ("marker", "expected"),
    [
        ("Full-time", JobType.FULL_TIME),
        ("Part-time", JobType.PART_TIME),
        ("Contract", JobType.CONTRACT),
        ("Temporary", JobType.TEMPORARY),
        ("Internship", JobType.INTERNSHIP),
        ("Self-employed", JobType.OTHER),
        ("Freelance/Temp", JobType.OTHER),
        ("FULL-TIME", JobType.FULL_TIME),
        ("  Full-time  ", JobType.FULL_TIME),
    ],
)
def test_parse_job_type(
    marker: str,
    expected: JobType,
) -> None:
    assert parse_job_types([marker]) == [expected]


def test_unknown_job_type() -> None:
    assert parse_job_types(["Be an early applicant"]) is None


def test_duplicate_job_types() -> None:
    assert parse_job_types(["Full-time", "Full-time"]) == [JobType.FULL_TIME]


def test_multiple_job_types() -> None:
    assert parse_job_types(["Full-time", "Part-time"]) == [
        JobType.FULL_TIME,
        JobType.PART_TIME,
    ]


@pytest.mark.parametrize(
    "location",
    [
        "Homeoffice",
        "Home Office",
        "Remote",
        "Fully Remote",
        "100% Remote",
        "Work From Home",
    ],
)
def test_remote_location(location: str) -> None:
    assert parse_remote_location(location) is True


@pytest.mark.parametrize(
    "location",
    [
        "Berlin",
        "Frankfurt am Main",
        "Hybrid",
        None,
    ],
)
def test_unknown_remote_status(
    location: str | None,
) -> None:
    assert parse_remote_location(location) is None
