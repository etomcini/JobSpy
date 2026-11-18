import pytest

from jobspy.xing.search import parse_search_url


def test_parse_berlin_search() -> None:
    url = (
        "https://www.xing.com/jobs/search/ki"
        "?id=48ea9d341fb84688f16a4277f8f2de4c"
        "&keywords=python%20developer"
        "&location=Berlin"
        "&cityId=2950159.e2912c"
    )

    result = parse_search_url(url)

    assert result.keywords == "python developer"
    assert result.location == "Berlin"
    assert result.city_id == "2950159.e2912c"
    assert result.search_id == ("48ea9d341fb84688f16a4277f8f2de4c")


def test_parse_munich_search() -> None:
    url = (
        "https://www.xing.com/jobs/search/ki"
        "?id=d1e94395ff2f2b90b75c64416aa07b4c"
        "&keywords=python%20developer"
        "&location=Munich"
        "&cityId=2867714.724c7f"
    )

    result = parse_search_url(url)

    assert result.keywords == "python developer"
    assert result.location == "Munich"
    assert result.city_id == "2867714.724c7f"


def test_search_without_location() -> None:
    url = "https://www.xing.com/jobs/search/ki?keywords=fastapi"

    result = parse_search_url(url)

    assert result.keywords == "fastapi"
    assert result.location is None
    assert result.city_id is None
    assert result.search_id is None


@pytest.mark.parametrize(
    "url",
    [
        "http://www.xing.com/jobs/search/ki?keywords=python",
        "https://example.com/jobs/search/ki?keywords=python",
        "https://www.xing.com/jobs/search/ki",
        "https://www.xing.com/profile/example",
    ],
)
def test_invalid_search_urls(url: str) -> None:
    with pytest.raises(ValueError):
        parse_search_url(url)
