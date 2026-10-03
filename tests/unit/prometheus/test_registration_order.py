"""HTTP instrumentation callbacks must be registered before middleware is installed."""

import pytest
from prometheus_client import CollectorRegistry
from starlette.applications import Starlette

from app.prometheus import PrometheusManager


def test_http_instrumentation_cannot_be_added_after_middleware() -> None:
    """Callbacks after ``add_middleware`` never reach the already-installed ASGI wrapper."""
    manager = PrometheusManager(registry=CollectorRegistry())
    manager.add_middleware(Starlette())

    def unused_callback(*_args: object, **_kwargs: object) -> None:
        """No-op callback used only to exercise the registration guard."""

    with pytest.raises(RuntimeError, match="before add_middleware"):
        manager.add_http_instrumentation(unused_callback)
