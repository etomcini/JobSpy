from __future__ import annotations

from urllib.parse import urlsplit

from requests import Session

from jobspy.util import check_status


class XingClient:
    """HTTP transport for XING job pages."""

    BASE_URL = "https://www.xing.com"
    DEFAULT_TIMEOUT = 15

    def __init__(
        self,
        session: Session,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")

        self.session = session
        self.timeout = timeout

    def get_html(self, url: str) -> str:
        """Retrieve an HTML document from an allowed XING URL."""

        parsed = urlsplit(url)

        if (
            parsed.scheme != "https"
            or parsed.hostname != "www.xing.com"
            or parsed.port is not None
            or not parsed.path.startswith("/jobs/")
        ):
            raise ValueError("Invalid XING job URL")

        response = self.session.get(
            url,
            timeout=self.timeout,
            allow_redirects=False,
        )

        check_status(response)

        return response.text
