import pytest

from jobspy.xing.graphql_parser import parse_graphql_job
from jobspy.xing.normalization import (
    normalize_job_id,
    safe_dict,
)


def make_job_detail(**overrides: object) -> dict:
    detail = {
        "id": "12345.abc",
        "url": "https://www.xing.com/jobs/python-developer-12345",
        "title": "Python Developer",
        "companyInfo": {
            "companyNameOverride": "Example Company",
        },
    }

    detail.update(overrides)

    return {"jobDetail": detail}


def test_graphql_normalizes_text() -> None:
    job = parse_graphql_job(
        make_job_detail(
            title="  Senior   Python\nDeveloper  ",
            companyInfo={"companyNameOverride": "  Example   Company  "},
        )
    )

    assert job.title == "Senior Python Developer"
    assert job.company == "Example Company"


def test_graphql_normalizes_url() -> None:
    job = parse_graphql_job(
        make_job_detail(
            url=("https://xing.com/jobs/python-developer-12345?tracking=example")
        )
    )

    assert job.job_url == ("https://www.xing.com/jobs/python-developer-12345")


@pytest.mark.parametrize(
    "field",
    [
        "companyInfo",
        "location",
        "employmentType",
        "salary",
        "application",
    ],
)
def test_graphql_handles_malformed_optional_data(field: str) -> None:
    job = parse_graphql_job(make_job_detail(**{field: "invalid"}))

    assert job.id == "xing-12345"
    assert job.title == "Python Developer"


def test_graphql_rejects_empty_title() -> None:
    with pytest.raises(ValueError, match="Missing job title"):
        parse_graphql_job(make_job_detail(title="   "))


def test_normalize_job_id() -> None:
    assert normalize_job_id("12345.abc") == "xing-12345"
    assert normalize_job_id("12345") == "xing-12345"
    assert normalize_job_id(None) is None


def test_safe_dict() -> None:
    assert safe_dict({"value": 1}) == {"value": 1}
    assert safe_dict(None) == {}
    assert safe_dict("invalid") == {}
