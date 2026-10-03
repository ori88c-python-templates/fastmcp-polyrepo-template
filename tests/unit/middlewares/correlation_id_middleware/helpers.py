"""Build a tiny Starlette app that logs once per request through a given manager."""

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.logger import LogManager
from app.middlewares.correlation_id_middleware import CorrelationIdMiddleware


def build_logging_app(log_manager: LogManager) -> Starlette:
    """Mount a single ``/ping`` handler behind ``CorrelationIdMiddleware``.

    Args:
        log_manager: Manager the handler logs through. Tests inspect its stream
            for the bound ``correlation_id``.

    Returns:
        An application whose only interesting behaviour is one log line per GET.
    """
    app = Starlette()

    async def ping(_request: Request) -> JSONResponse:
        """Emit one record so tests can read the bound correlation id.

        Args:
            _request: Required by Starlette. Unused.

        Returns:
            A body the tests ignore; the log line is the assertion surface.
        """
        log_manager.get_child_logger("ping").info("ping.ok")
        return JSONResponse({"ok": True})

    app.add_route("/ping", ping)
    app.add_middleware(CorrelationIdMiddleware)
    return app
