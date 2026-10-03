"""Pytest fixtures for Redis and the integration event loop.

Throwaway Redis lives in ``tests/``. Future services should take
``redis_client`` from here.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

from app.clients import RedisClient
from app.config import RedisConfig
from app.logger import LogManager

if TYPE_CHECKING:
    from tests.throwaway_stores import ThrowawayStores

_INTEGRATION_ROOT: Final = Path(__file__).resolve().parent


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark every test under this directory as ``integration``.

    Args:
        items: The collected session. Tests outside this tree are left unmarked.
    """
    marker = pytest.mark.integration
    for item in items:
        try:
            item.path.relative_to(_INTEGRATION_ROOT)
        except ValueError:
            continue
        item.add_marker(marker)


@pytest.fixture(scope="session")
def redis_config(throwaway_stores: ThrowawayStores) -> RedisConfig:
    """Expose the session Redis settings for any service under test.

    Args:
        throwaway_stores: Session container.

    Returns:
        Settings that reach the throwaway Redis, not Compose.
    """
    return throwaway_stores.redis


@pytest.fixture
async def redis_client(
    redis_config: RedisConfig,
    log_manager: LogManager,
) -> AsyncGenerator[RedisClient]:
    """Open a real redis-py pool against the session Redis.

    Args:
        redis_config: Session container settings.
        log_manager: Supplies the client child logger.

    Yields:
        A started client. ``stop`` runs even if the test fails.
    """
    client = RedisClient(
        redis_config,
        log_manager.get_child_logger("RedisClient"),
    )
    await client.start()
    try:
        yield client
    finally:
        await client.stop()


@pytest.fixture(autouse=True)
async def _flush_redis(  # pyright: ignore[reportUnusedFunction]
    redis_client: RedisClient,
) -> None:
    """Empty Redis before every test so a later service does not inherit keys.

    Args:
        redis_client: Started pool for ``FLUSHDB``.
    """
    await redis_client.raw.flushdb()  # pyright: ignore[reportUnknownMemberType]
