from pathlib import Path

from jobspy.xing.detail import extract_xing_html_description

FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "xing"
    / "job_detail_html_sections.html"
)


def test_extract_html_description() -> None:
    html = FIXTURE.read_text(encoding="utf-8")

    description = extract_xing_html_description(html)

    assert description is not None
    assert "Über uns" in description
    assert "Diese Aufgaben erwarten Dich" in description
    assert "Wir suchen jemanden mit" in description
    assert "Python" in description

    # Exclude unrelated page content.
    assert "Similar jobs" not in description
    assert "About the company" not in description
