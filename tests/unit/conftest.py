"""Shared fixtures for in-process unit tests."""

import pytest

from app.clients import RedisClient
from app.logger import LogManager
from app.state import AppState
from tests.unit.app_state_factory import AppStateFactory, build_app_state


@pytest.fixture
def make_app_state(log_manager: LogManager) -> AppStateFactory:
    """Provide a factory that builds AppState with an AsyncMock Redis client.

    Args:
        log_manager: Buffer-backed manager shared by every state this factory builds.

    Returns:
        A callable that accepts an optional ``redis`` client and fills in a
        specced AsyncMock when the caller omits it.
    """

    def factory(*, redis: RedisClient | None = None) -> AppState:
        """Build AppState, forwarding only the Redis client the caller supplied.

        Args:
            redis: Injected Redis client, or ``None`` for a specced AsyncMock.

        Returns:
            Frozen application state for a test ASGI app.
        """
        return build_app_state(log_manager, redis=redis)

    return factory
