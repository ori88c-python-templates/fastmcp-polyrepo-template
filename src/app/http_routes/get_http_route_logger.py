"""Child logger named after the matched custom HTTP route.

This is not a logger for MCP tools or resources. A tool name is a protocol
field on ``tools/call``. A resource name is a URI. Neither appears on the ASGI
scope. A primitive that must log receives a child logger on the feature's
``<Feature>McpLoggers`` dataclass, injected into its registrator.
"""

from starlette.requests import Request
from starlette.routing import Route
from structlog.typing import FilteringBoundLogger

from app.state import get_app_state


def get_http_route_logger(request: Request) -> FilteringBoundLogger:
    """Return a child logger whose ``context`` is the matched HTTP route's name.

    Only custom HTTP routes use this. MCP primitives do not.

    ``custom_route(..., name=)`` sets the Starlette route name. Set ``name=``
    explicitly; a generated name would follow the function and churn whenever
    a handler is renamed.

    Args:
        request: The in-flight HTTP request. Used to reach both the matched
            route and the process-wide ``LogManager`` on application state.

    Returns:
        A logger from that ``LogManager``. The correlation id is not bound here:
        ``CorrelationIdMiddleware`` already put it in structlog's contextvars,
        and every child logger on this request picks it up.

    Raises:
        RuntimeError: If the matched route has no name. That is a registration
            bug, not a client error.
    """
    name = _matched_http_route_name(request)
    if name is None or name == "":
        raise RuntimeError("Matched HTTP route has no name; pass name= when registering it.")
    return get_app_state(request).log_manager.get_child_logger(name)


def _matched_http_route_name(request: Request) -> str | None:
    """Return the name of the custom HTTP route that matched ``request``.

    Two places can carry that name, and they are not two kinds of MCP route:

    - ``scope["route"]`` is the route object FastAPI used to put on the ASGI
      scope before calling a path function. Starlette's router does not set it.
      It only copies ``endpoint`` and ``path_params``. This process never sets
      ``scope["route"]``. The branch uses it when a scope already carries the
      route object.
    - ``scope["endpoint"]`` is what ``custom_route`` actually hits. Starlette
      sets it to the handler function. The matching ``Route`` is the one with
      that same function, and its ``name`` is the ``name=`` passed to
      ``custom_route``.

    Args:
        request: The in-flight HTTP request.

    Returns:
        The route name, or ``None`` when the match cannot be named.
    """
    mounted = request.scope.get("route")
    mounted_name = getattr(mounted, "name", None)
    if isinstance(mounted_name, str) and mounted_name:
        return mounted_name

    endpoint = request.scope.get("endpoint")
    for candidate in request.app.routes:
        if isinstance(candidate, Route) and candidate.endpoint is endpoint:
            return candidate.name
    return None
