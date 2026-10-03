"""HTTP through the real application against throwaway Redis.

Probe tests reuse ``client``. MCP tests reuse ``open_mcp_client`` from
``tests/e2e/mcp_primitives/conftest.py``. Both talk to this session app.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette

from app.config import AppConfig
from app.lifecycle import LifecycleManager
from app.state import get_app_state_from_app

if TYPE_CHECKING:
    from tests.throwaway_stores import ThrowawayStores

_E2E_ROOT: Final = Path(__file__).resolve().parent


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark every test under this directory as ``e2e``.

    Args:
        items: The collected session. Tests outside this tree are left unmarked.
    """
    e2e_marker = pytest.mark.e2e
    for item in items:
        try:
            item.path.relative_to(_E2E_ROOT)
        except ValueError:
            continue
        item.add_marker(e2e_marker)


@pytest.fixture(scope="session")
def app_config(throwaway_stores: ThrowawayStores) -> AppConfig:
    """Build the config the session application and the MCP client share.

    Args:
        throwaway_stores: Session Redis container.

    Returns:
        Config pointed at throwaway Redis, with the default MCP path.
    """
    return AppConfig(redis=throwaway_stores.redis)


@pytest.fixture(scope="session")
def app(app_config: AppConfig) -> Starlette:
    """Build the real application pointed at the session Redis.

    Args:
        app_config: Session config, including the MCP path the client calls.

    Returns:
        An application from ``LifecycleManager``. Lifespan has not run yet.
    """
    return LifecycleManager(app_config).create_app()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def client(app: Starlette) -> AsyncGenerator[AsyncClient]:
    """Start the app lifespan once and yield an HTTP client.

    httpx 0.28's ``ASGITransport`` does not run lifespan, so this fixture
    enters ``lifespan_context`` itself. FastMCP's session manager uses an
    anyio cancel scope that must be exited by the task that entered it.
    pytest-asyncio finalizes this generator on another task, so the scope
    lives on ``_run_lifespan`` for the whole session.

    Args:
        app: Session application whose clients are started here.

    Yields:
        A client bound to the running application.
    """
    started = asyncio.Event()
    stop = asyncio.Event()
    clients: list[AsyncClient] = []
    startup_error: list[BaseException] = []

    async def _run_lifespan() -> None:
        """Enter the app lifespan and hold the client until ``stop`` is set."""
        try:
            async with (
                app.router.lifespan_context(app),
                AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://e2e.test",
                ) as http,
            ):
                clients.append(http)
                started.set()
                await stop.wait()
        except BaseException as exc:
            startup_error.append(exc)
            started.set()
            raise

    task = asyncio.create_task(_run_lifespan())
    await started.wait()
    if startup_error:
        await task
        raise startup_error[0]
    try:
        yield clients[0]
    finally:
        stop.set()
        await task


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def _flush_redis(  # pyright: ignore[reportUnusedFunction]
    client: AsyncClient,
    app: Starlette,
) -> None:
    """Empty Redis before every test so a later feature does not inherit keys.

    Args:
        client: Session client. Requested so lifespan has already started Redis.
        app: Session application whose Redis pool is flushed.
    """
    del client
    await get_app_state_from_app(app).clients.redis.raw.flushdb()  # pyright: ignore[reportUnknownMemberType]
