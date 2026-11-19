from __future__ import annotations

from dataclasses import dataclass

from jobspy.xing.normalization import (
    normalize_currency,
    normalize_salary_amount,
    safe_dict,
)


@dataclass(frozen=True)
class XingSalary:
    min_amount: float | None = None
    max_amount: float | None = None
    currency: str | None = None
    salary_source: str | None = None


def parse_graphql_salary(value: object) -> XingSalary:
    """Parse salary information from a XING GraphQL job."""

    salary = safe_dict(value)
    salary_type = salary.get("__typename")

    min_amount: float | None = None
    max_amount: float | None = None

    if salary_type in {"SalaryRange", "SalaryEstimate"}:
        min_amount = normalize_salary_amount(salary.get("minimum"))
        max_amount = normalize_salary_amount(salary.get("maximum"))

    elif salary_type == "Salary":
        amount = normalize_salary_amount(salary.get("amount"))
        min_amount = amount
        max_amount = amount

    else:
        return XingSalary()

    if min_amount is None and max_amount is None:
        return XingSalary()

    if min_amount is not None and max_amount is not None and min_amount > max_amount:
        return XingSalary()

    source = "estimated" if salary_type == "SalaryEstimate" else "direct_data"

    return XingSalary(
        min_amount=min_amount,
        max_amount=max_amount,
        currency=normalize_currency(salary.get("currency")),
        salary_source=source,
    )
