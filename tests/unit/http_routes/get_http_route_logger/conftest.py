"""Shared fixtures for the HTTP route child-logger tests."""

from collections.abc import AsyncGenerator

import pytest
from fastmcp import FastMCP
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette

from app.http_routes import register_k8s_probes
from app.state import APP_STATE_ATTRIBUTE
from tests.unit.app_state_factory import AppStateFactory


@pytest.fixture
def app(make_app_state: AppStateFactory) -> Starlette:
    """Register the probes on an app whose logs are inspectable.

    Readiness is the route that logs. Liveness does not, and it must keep
    working on an application that has no state.

    Args:
        make_app_state: Shared factory that fills AppState with injected doubles.

    Returns:
        An application with ``AppState`` attached.
    """
    mcp = FastMCP("probes")
    register_k8s_probes(mcp, include_in_schema=True)
    application = mcp.http_app(
        stateless_http=True,
        json_response=True,
        host_origin_protection=False,
    )
    setattr(application.state, APP_STATE_ATTRIBUTE, make_app_state())
    return application


@pytest.fixture
async def client(app: Starlette) -> AsyncGenerator[AsyncClient]:
    """Provide a client that speaks ASGI directly to ``app``.

    Args:
        app: The application to send requests to.

    Yields:
        A client bound to that application.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://route-logger.test",
    ) as http_client:
        yield http_client
