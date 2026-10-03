"""Assemble a real UserNotesService against the session Redis."""

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
def user_notes_service(
    redis_client: RedisClient,
    log_manager: LogManager,
    user_notes_metrics: UserNotesMetrics,
) -> UserNotesService:
    """Provide the real service wired to the session Redis.

    Args:
        redis_client: Started pool against Testcontainers Redis.
        log_manager: Buffer-backed manager from ``tests/conftest.py``.
        user_notes_metrics: Collectors on this test's private registry.

    Returns:
        A ``UserNotesService`` that talks to real Redis.
    """
    return UserNotesService(
        redis_client,
        log_manager.get_child_logger("UserNotesService"),
        user_notes_metrics,
    )
