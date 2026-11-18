class XingPaginationError(Exception):
    """Base exception for XING pagination failures."""


class XingPageLoadError(XingPaginationError):
    """The injected page loader failed."""


class XingGraphQLError(XingPaginationError):
    """The GraphQL response contains errors or invalid data."""
