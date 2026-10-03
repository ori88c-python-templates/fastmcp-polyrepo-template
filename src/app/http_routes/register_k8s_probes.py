"""Register Kubernetes liveness and readiness probes on a FastMCP server.

Deliberately unprefixed. Probes are infrastructure rather than API surface: kubelet is
configured with these paths in a manifest, and versioning the MCP endpoint must never
require a deployment change. An exact, unprefixed path is also the easiest thing to exempt
from authentication later.
"""

from http import HTTPStatus

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import LIVEZ_ENDPOINT, READYZ_ENDPOINT
from app.http_routes.get_http_route_logger import get_http_route_logger
from app.models.k8s_probes import K8sProbeResponse
from app.state import get_app_state

_LIVE_ROUTE_NAME = "k8s-probe-router.live"
_READY_ROUTE_NAME = "k8s-probe-router.ready"
_REDIS_HEALTH_DETAIL = "Redis failed a health check."


def register_k8s_probes(mcp: FastMCP, *, include_in_schema: bool) -> None:
    """Register ``GET /livez`` and ``GET /readyz`` on ``mcp``.

    Call this before ``http_app``: custom routes are copied onto the Starlette
    app at that moment.

    Args:
        mcp: The server the composition root is building.
        include_in_schema: Whether the probe routes are marked for schema.
            Staging and production pass false. Kubelet still calls the paths.
    """

    @mcp.custom_route(
        LIVEZ_ENDPOINT,
        methods=["GET"],
        name=_LIVE_ROUTE_NAME,
        include_in_schema=include_in_schema,
    )
    async def liveness_probe(_request: Request) -> JSONResponse:
        """Report whether the process is still able to serve at all.

        Never check an external resource here, and never add one later. Failing this probe
        makes kubelet kill and restart the container, and a restart cannot fix a Redis
        outage. Checking dependencies here turns a partial outage into a
        fleet-wide crash-loop, taking down every pod at once and hammering the dependency
        with reconnects exactly when it is least able to cope.

        The only honest failure for liveness is a process that can no longer recover on its
        own: a wedged event loop, a deadlock, exhausted memory. Returning at all already
        demonstrates the event loop is scheduling work.

        Args:
            _request: Required by ``custom_route``. Unused: liveness must not touch
                application state.

        Returns:
            A 200 JSON body for as long as the process is running.
        """
        return JSONResponse(K8sProbeResponse().model_dump())

    @mcp.custom_route(
        READYZ_ENDPOINT,
        methods=["GET"],
        name=_READY_ROUTE_NAME,
        include_in_schema=include_in_schema,
    )
    async def readiness_probe(request: Request) -> JSONResponse:
        """Report whether this instance can currently serve traffic.

        This is where dependency checks belong. Failing readiness removes the pod from the
        Service endpoints without killing it, so traffic is routed to healthy instances and
        returns automatically once the dependency recovers.

        Check only what a request genuinely cannot be served without, and check it cheaply:
        this runs on every probe interval, on every pod. A ``PING`` against an existing
        pooled connection, not a fresh connection or a real query.

        Args:
            request: Used to reach the shared clients and the route logger on
                application state.

        Returns:
            A 200 JSON body when Redis answers, or 503 when the ping fails.
        """
        get_http_route_logger(request).info("readiness.probe")
        clients = get_app_state(request).clients
        try:
            await clients.redis.ping()
        except Exception:
            return JSONResponse(
                {"detail": _REDIS_HEALTH_DETAIL},
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            )
        return JSONResponse(K8sProbeResponse().model_dump())
