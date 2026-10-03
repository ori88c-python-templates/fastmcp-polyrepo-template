"""Assemble a real UserNotesService from a mocked Redis client."""

from typing import cast
from unittest.mock import AsyncMock

import pytest
from prometheus_client import CollectorRegistry

from app.clients import RedisClient
from app.logger import LogManager
from app.metrics import UserNotesMetrics
from app.services import UserNotesService


@pytest.fixture
def collector_registry() -> CollectorRegistry:
    """Provide a private collector so metric tests cannot collide.

    Returns:
        An empty registry bound to this test's ``UserNotesMetrics``.
    """
    return CollectorRegistry()


@pytest.fixture
def user_notes_metrics(collector_registry: CollectorRegistry) -> UserNotesMetrics:
    """Provide collectors registered on the test's private registry.

    Args:
        collector_registry: Empty registry for this test.

    Returns:
        Metrics the service under test will increment.
    """
    return UserNotesMetrics(registry=collector_registry)


@pytest.fixture
def redis_client() -> AsyncMock:
    """Provide a Redis client whose list methods are awaitable mocks.

    Returns:
        An ``AsyncMock`` specced on ``RedisClient``.
    """
    return AsyncMock(spec=RedisClient)


@pytest.fixture
def user_notes_service(
    redis_client: AsyncMock,
    log_manager: LogManager,
    user_notes_metrics: UserNotesMetrics,
) -> UserNotesService:
    """Provide the real service wired to mocked Redis.

    Args:
        redis_client: Client whose list methods are awaitable mocks.
        log_manager: Buffer-backed manager from the unit-test root.
        user_notes_metrics: Collectors on this test's private registry.

    Returns:
        A ``UserNotesService`` that never opens a socket.
    """
    return UserNotesService(
        cast(RedisClient, redis_client),
        log_manager.get_child_logger("UserNotesService"),
        user_notes_metrics,
    )
