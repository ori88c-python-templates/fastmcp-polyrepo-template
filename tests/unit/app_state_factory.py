"""Build a typed AppState for in-process HTTP route tests."""

from typing import Protocol, cast
from unittest.mock import AsyncMock

from prometheus_client import CollectorRegistry

from app.clients import RedisClient
from app.logger import LogManager
from app.metrics import UserNotesMetrics
from app.services import UserNotesService
from app.state import AppClients, AppServices, AppState


class AppStateFactory(Protocol):
    """Callable that fills AppState, defaulting omitted dependencies to AsyncMocks."""

    def __call__(
        self,
        *,
        redis: RedisClient | None = None,
    ) -> AppState:
        """Assemble state from the given dependencies.

        Args:
            redis: Injected Redis client. ``None`` means a specced AsyncMock.

        Returns:
            Frozen application state suitable for attaching to a test ASGI app.
        """
        ...


def build_app_state(
    log_manager: LogManager,
    *,
    redis: RedisClient | None = None,
) -> AppState:
    """Assemble AppState, substituting an AsyncMock for an omitted Redis client.

    Args:
        log_manager: Already-built manager (usually writing to a buffer).
        redis: Injected Redis client. Defaults to a specced AsyncMock.

    Returns:
        Frozen application state suitable for attaching to a test ASGI app.
    """
    chosen = redis if redis is not None else cast(RedisClient, AsyncMock(spec=RedisClient))
    return AppState(
        clients=AppClients(redis=chosen),
        services=AppServices(
            user_notes=UserNotesService(
                chosen,
                log_manager.get_child_logger("UserNotesService"),
                UserNotesMetrics(registry=CollectorRegistry()),
            ),
        ),
        log_manager=log_manager,
    )
