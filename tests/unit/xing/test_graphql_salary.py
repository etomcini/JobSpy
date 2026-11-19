
import pytest

from jobspy.xing.normalization import normalize_currency
from jobspy.xing.salary import XingSalary, parse_graphql_salary


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("EUR", "EUR"),
        ("eur", "EUR"),
        (" € ", "EUR"),
        ("USD", "USD"),
        ("$", "USD"),
        ("GBP", "GBP"),
        ("£", "GBP"),
        ("CHF", "CHF"),
        ("INVALID", None),
        (None, None),
        (123, None),
    ],
)
def test_normalize_currency(
    value: object,
    expected: str | None,
) -> None:
    assert normalize_currency(value) == expected


def test_salary_range() -> None:
    result = parse_graphql_salary(
        {
            "__typename": "SalaryRange",
            "minimum": 50000,
            "maximum": 70000,
            "currency": "eur",
        }
    )

    assert result == XingSalary(
        min_amount=50000.0,
        max_amount=70000.0,
        currency="EUR",
        salary_source="direct_data",
    )


def test_salary_estimate() -> None:
    result = parse_graphql_salary(
        {
            "__typename": "SalaryEstimate",
            "minimum": 45000,
            "maximum": 65000,
            "currency": "EUR",
        }
    )

    assert result.salary_source == "estimated"
    assert result.min_amount == 45000.0
    assert result.max_amount == 65000.0


def test_single_salary() -> None:
    result = parse_graphql_salary(
        {
            "__typename": "Salary",
            "amount": 60000,
            "currency": "EUR",
        }
    )

    assert result.min_amount == 60000.0
    assert result.max_amount == 60000.0


def test_partial_salary_range() -> None:
    result = parse_graphql_salary(
        {
            "__typename": "SalaryRange",
            "minimum": 50000,
            "maximum": None,
            "currency": "EUR",
        }
    )

    assert result.min_amount == 50000.0
    assert result.max_amount is None


@pytest.mark.parametrize(
    "value",
    [
        None,
        "invalid",
        {},
        {"__typename": "Unknown", "amount": 50000},
        {
            "__typename": "SalaryRange",
            "minimum": 80000,
            "maximum": 50000,
            "currency": "EUR",
        },
        {
            "__typename": "Salary",
            "amount": -5000,
            "currency": "EUR",
        },
    ],
)
def test_invalid_salary_returns_empty(value: object) -> None:
    assert parse_graphql_salary(value) == XingSalary()


def test_invalid_currency_preserves_amounts() -> None:
    result = parse_graphql_salary(
        {
            "__typename": "Salary",
            "amount": 60000,
            "currency": "UNKNOWN",
        }
    )

    assert result.min_amount == 60000.0
    assert result.max_amount == 60000.0
    assert result.currency is None
