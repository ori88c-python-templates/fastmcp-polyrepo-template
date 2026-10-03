"""FastMCP client bound to the session application.

Entered inside the test, on the test's task. A session-scoped client would be
torn down on a different task from the one that opened its anyio cancel scope.
"""

from collections.abc import AsyncGenerator, Callable, Mapping
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Final

import httpx2
import pytest
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from httpx import AsyncClient
from starlette.applications import Starlette

from app.config import AppConfig

_BASE_URL: Final = "http://e2e.test"

type OpenMcpClient = Callable[
    [Mapping[str, str]],
    AbstractAsyncContextManager[Client[StreamableHttpTransport]],
]


@pytest.fixture
def open_mcp_client(
    app: Starlette,
    app_config: AppConfig,
    client: AsyncClient,
) -> OpenMcpClient:
    """Open a streamable HTTP client against the running app.

    ``httpx`` 0.28 serves probes. FastMCP's transport speaks ``httpx2``, so
    this factory returns an ``httpx2`` client on an ASGI transport. Headers
    are per call because each caller has its own tenant and user.

    Args:
        app: Session application. Requests are delivered in-process.
        app_config: Supplies ``MCP_PATH`` so the URL matches the app.
        client: Session HTTP client. Requested so the lifespan has started Redis.

    Returns:
        A context manager factory. The caller passes inbound HTTP headers.
    """
    del client
    url = f"{_BASE_URL}{app_config.server.MCP_PATH}"

    @asynccontextmanager
    async def open_client(
        headers: Mapping[str, str],
    ) -> AsyncGenerator[Client[StreamableHttpTransport]]:
        """Connect one MCP session with ``headers``.

        Args:
            headers: Inbound headers for this caller. Identity headers are
                included by the tests that need them.

        Yields:
            A connected FastMCP client.
        """

        def http_client(
            headers: dict[str, str] | None = None,
            timeout: httpx2.Timeout | None = None,
            auth: httpx2.Auth | None = None,
            *,
            follow_redirects: bool = True,
        ) -> httpx2.AsyncClient:
            """Route MCP HTTP through the session ASGI app.

            Args:
                headers: Headers the transport merged for this connection.
                timeout: Optional httpx timeout from the transport.
                auth: Unused for these tests. Accepted because the transport
                    passes it.
                follow_redirects: Passed by ``StreamableHttpTransport``.

            Returns:
                A client whose transport is the session application.
            """
            return httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=app),
                base_url=_BASE_URL,
                headers=headers,
                timeout=timeout,
                auth=auth,
                follow_redirects=follow_redirects,
            )

        transport = StreamableHttpTransport(
            url,
            headers=dict(headers),
            httpx_client_factory=http_client,
        )
        async with Client(transport) as mcp:
            yield mcp

    return open_client
