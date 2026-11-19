import pytest

from jobspy.xing.normalization import (
    normalize_text,
    normalize_xing_job_url,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Python Developer", "Python Developer"),
        ("  Senior   Python  Developer  ", "Senior Python Developer"),
        ("Berlin\nGermany", "Berlin Germany"),
        ("", None),
        ("   ", None),
        (None, None),
        (123, None),
    ],
)
def test_normalize_text(value: object, expected: str | None) -> None:
    assert normalize_text(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            "https://www.xing.com/jobs/python-developer-123",
            "https://www.xing.com/jobs/python-developer-123",
        ),
        (
            "https://xing.com/jobs/python-developer-123?tracking=abc",
            "https://www.xing.com/jobs/python-developer-123",
        ),
        (
            "https://www.xing.com/jobs/python-developer-123#details",
            "https://www.xing.com/jobs/python-developer-123",
        ),
        (
            "http://www.xing.com/jobs/python-developer-123",
            None,
        ),
        (
            "https://example.com/jobs/python-developer-123",
            None,
        ),
        (
            "https://www.xing.com.evil.com/jobs/python-developer-123",
            None,
        ),
        (
            "https://www.xing.com/profile/example",
            None,
        ),
        ("", None),
        (None, None),
    ],
)
def test_normalize_xing_job_url(
    value: object,
    expected: str | None,
) -> None:
    assert normalize_xing_job_url(value) == expected
