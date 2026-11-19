from unittest.mock import Mock

import pytest
from requests import Session

from jobspy.xing.client import XingClient


@pytest.fixture
def session() -> Mock:
    return Mock(spec=Session)


def test_get_html_success(session: Mock) -> None:
    response = Mock()
    response.status_code = 200
    response.text = "<html><body>Job listing</body></html>"

    session.get.return_value = response

    client = XingClient(session)

    html = client.get_html("https://www.xing.com/jobs/example-job-123")

    assert html == "<html><body>Job listing</body></html>"
    session.get.assert_called_once_with(
        "https://www.xing.com/jobs/example-job-123",
        timeout=15,
        allow_redirects=False,
    )


def test_get_html_calls_status_checker(
    session: Mock,
    mocker,
) -> None:
    response = Mock()
    response.status_code = 200
    response.text = "<html></html>"

    session.get.return_value = response

    check = mocker.patch("jobspy.xing.client.check_status")

    client = XingClient(session)
    client.get_html("https://www.xing.com/jobs/example-job-123")

    check.assert_called_once_with(response)


def test_get_html_propagates_status_error(
    session: Mock,
    mocker,
) -> None:
    response = Mock()
    session.get.return_value = response

    check = mocker.patch(
        "jobspy.xing.client.check_status",
        side_effect=RuntimeError("HTTP 403"),
    )

    client = XingClient(session)

    with pytest.raises(RuntimeError, match="HTTP 403"):
        client.get_html("https://www.xing.com/jobs/example-job-123")

    check.assert_called_once_with(response)


def test_get_html_propagates_connection_error(
    session: Mock,
) -> None:
    from requests.exceptions import ConnectionError

    session.get.side_effect = ConnectionError("Connection failed")

    client = XingClient(session)

    with pytest.raises(ConnectionError):
        client.get_html("https://www.xing.com/jobs/example-job-123")


@pytest.mark.parametrize(
    "url",
    [
        "http://www.xing.com/jobs/example-123",
        "https://example.com/jobs/example-123",
        "https://www.xing.com.evil.com/jobs/example-123",
        "https://www.xing.com/profile/example",
        "https://www.xing.com:8443/jobs/example-123",
    ],
)
def test_rejects_invalid_urls(
    session: Mock,
    url: str,
) -> None:
    client = XingClient(session)

    with pytest.raises(ValueError, match="Invalid XING job URL"):
        client.get_html(url)

    session.get.assert_not_called()


def test_custom_timeout(session: Mock) -> None:
    response = Mock()
    response.status_code = 200
    response.text = "<html></html>"
    session.get.return_value = response

    client = XingClient(session, timeout=30)

    client.get_html("https://www.xing.com/jobs/example-job-123")

    session.get.assert_called_once_with(
        "https://www.xing.com/jobs/example-job-123",
        timeout=30,
        allow_redirects=False,
    )


def test_invalid_timeout(session: Mock) -> None:
    with pytest.raises(ValueError, match="timeout must be positive"):
        XingClient(session, timeout=0)


def test_redirect_not_followed(session: Mock) -> None:
    response = Mock()
    response.status_code = 302
    response.text = ""
    session.get.return_value = response

    client = XingClient(session)

    with pytest.raises(
        ValueError,
        match="response status code 302",
    ):
        client.get_html("https://www.xing.com/jobs/example-job-123")

    session.get.assert_called_once_with(
        "https://www.xing.com/jobs/example-job-123",
        timeout=15,
        allow_redirects=False,
    )
