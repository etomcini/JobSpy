
import pytest

from jobspy.xing.normalization import normalize_xing_location


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Berlin + 0 weitere", "Berlin"),
        ("Berlin + 2 weitere", "Berlin"),
        ("Berlin + 1 weiterer", "Berlin"),
        ("Berlin · + 3 weitere", "Berlin"),
        ("München + 0 weitere", "München"),
        ("Frankfurt am Main", "Frankfurt am Main"),
        ("Berlin, Deutschland", "Berlin, Deutschland"),
        ("  Berlin   + 0 weitere  ", "Berlin"),
        ("", None),
        ("   ", None),
        (None, None),
        (123, None),
    ],
)
def test_normalize_xing_location(
    raw: object,
    expected: str | None,
) -> None:
    assert normalize_xing_location(raw) == expected
