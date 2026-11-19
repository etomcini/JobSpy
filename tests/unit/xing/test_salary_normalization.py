import math

import pytest

from jobspy.xing.normalization import normalize_salary_amount


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (50000, 50000.0),
        (65000.50, 65000.50),
        (0, 0.0),
        (-100, None),
        ("50000", None),
        (None, None),
        (True, None),
        (False, None),
        (math.inf, None),
        (-math.inf, None),
        (math.nan, None),
    ],
)
def test_normalize_salary_amount(
    value: object,
    expected: float | None,
) -> None:
    assert normalize_salary_amount(value) == expected
