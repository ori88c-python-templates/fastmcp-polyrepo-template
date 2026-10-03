"""Build ``UserDetails`` from the inbound HTTP headers.

Shared by every MCP feature. There is no ASGI middleware for these headers:
FastMCP's ``CurrentHeaders()`` already exposes them to a ``Depends`` factory.
The factory is an async context manager so ``tenant_id`` and ``user_id`` stay
on the structlog context for the primitive call, then unbind.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastmcp.dependencies import CurrentHeaders

from app.config import TENANT_ID_HEADER, USER_ID_HEADER
from app.models.user_details import UserDetails


@asynccontextmanager
async def get_user_details(
    headers: dict[str, str] = CurrentHeaders(),  # noqa: B008
) -> AsyncGenerator[UserDetails]:
    """Yield the caller, with tenant and user bound on the log context.

    ``CurrentHeaders()`` lowercases names. A missing header is treated as empty
    so ``UserDetails`` rejects it before anything is bound. FastMCP keeps this
    context manager open until the primitive returns, so the primitive logger
    and the service logger both pick up the ids. The bind ends with the call.

    Args:
        headers: Inbound HTTP headers for this MCP call. FastMCP resolves
            ``CurrentHeaders()`` before the primitive body runs.

    Yields:
        The validated tenant and user.

    Raises:
        ValidationError: If either header is missing or blank.
    """
    user_details = UserDetails(
        tenant_id=headers.get(TENANT_ID_HEADER.lower(), "").strip(),
        user_id=headers.get(USER_ID_HEADER.lower(), "").strip(),
    )
    with structlog.contextvars.bound_contextvars(
        tenant_id=user_details.tenant_id,
        user_id=user_details.user_id,
    ):
        yield user_details
