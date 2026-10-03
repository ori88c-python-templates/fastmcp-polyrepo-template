"""Tiny Starlette app mirroring lifecycle's PrometheusManager wiring."""

from prometheus_client import CollectorRegistry
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import PrometheusConfig
from app.prometheus import (
    PrometheusManager,
    make_inbound_request_id_instrumentation,
)


def instrumented_app(
    registry: CollectorRegistry,
    config: PrometheusConfig | None = None,
) -> Starlette:
    """App with ``GET /ping`` and ``GET /metrics`` on a private collector.

    Mirrors ``LifecycleManager``'s Prometheus wiring: construct
    ``PrometheusManager``, then ``add_http_instrumentation``, then
    ``add_middleware``, then ``add_metrics_router``. Correlation id is covered
    in the middleware suite and is not this suite's subject.

    Args:
        registry: Private collector so this test cannot collide with another.
        config: Gzip for the scrape path. Defaults to ``PrometheusConfig()``.

    Returns:
        An application with ``GET /ping`` and ``GET /metrics``.
    """
    app = Starlette()

    async def ping(_request: Request) -> JSONResponse:
        """Return a body the tests ignore.

        Args:
            _request: Required by Starlette. Unused.

        Returns:
            A trivial JSON payload.
        """
        return JSONResponse({"ok": True})

    app.add_route("/ping", ping)

    prometheus = PrometheusManager(registry=registry)
    prometheus.add_http_instrumentation(
        make_inbound_request_id_instrumentation(prometheus.registry),
    )
    prometheus.add_middleware(app)
    prometheus.add_metrics_router(
        app,
        config if config is not None else PrometheusConfig(),
    )
    return app
