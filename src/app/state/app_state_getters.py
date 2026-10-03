"""Typed accessors that recover :class:`AppState` from the ASGI application's state bag."""

from typing import Final, cast

from starlette.applications import Starlette
from starlette.requests import Request

from app.state.app_state import AppServices, AppState

APP_STATE_ATTRIBUTE: Final = "app_state"


def get_app_state_from_app(app: Starlette) -> AppState:
    """Read the application state off ``app``, narrowed to its real type.

    This is the only place in the codebase that casts. Starlette stores application
    state in a bag whose ``__getattr__`` is typed to return ``Any``, so reading it
    anywhere else would silently poison every downstream expression with ``Any`` and
    disable the type checking this container exists to provide.

    Args:
        app: The application ``create_app`` built and attached the state to.

    Returns:
        The state attached during construction.

    Raises:
        AttributeError: If called against an application not built by ``create_app``,
            which is a wiring bug rather than a runtime condition to handle.
    """
    return cast(AppState, getattr(app.state, APP_STATE_ATTRIBUTE))


def get_app_state(request: Request) -> AppState:
    """Read the application state that owns ``request``.

    Args:
        request: The in-flight request.

    Returns:
        The state shared by every request this process serves. It is not per-request:
        the same instance is handed to every caller.
    """
    return get_app_state_from_app(request.app)


def get_app_services(request: Request) -> AppServices:
    """Read just the services, which is what a route handler almost always wants.

    Handlers call services, not clients; reaching past this into ``clients`` from a
    route means business logic is about to be written in the wrong layer.

    Args:
        request: The in-flight request.

    Returns:
        The application's services.
    """
    return get_app_state(request).services
