"""Compatibility exports for XING GraphQL pagination."""

from jobspy.xing.pagination import (
    GraphQLPageLoader,
    GraphQLPayload,
    WarningCallback,
    iter_graphql_pages,
)

__all__ = [
    "GraphQLPageLoader",
    "GraphQLPayload",
    "WarningCallback",
    "iter_graphql_pages",
]
