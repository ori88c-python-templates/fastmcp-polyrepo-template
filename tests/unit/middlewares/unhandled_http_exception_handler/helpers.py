"""Tiny Starlette app that can boom or 404, with the production exception handler."""

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.logger import LogManager
from app.middlewares import (
    CorrelationIdMiddleware,
    make_unhandled_http_exception_handler,
)


def build_unhandled_exception_app(log_manager: LogManager) -> Starlette:
    """App with ``GET /boom``, ``GET /missing``, and ``GET /ok``.

    Mirrors production: ``Exception`` handler first, then correlation id.

    Args:
        log_manager: Manager whose ``uvicorn`` child the handler logs through.

    Returns:
        An application whose unhandled errors become a generic 500.
    """
    app = Starlette()
    app.add_exception_handler(
        Exception,
        make_unhandled_http_exception_handler(log_manager.get_child_logger("uvicorn")),
    )

    async def boom(_request: Request) -> JSONResponse:
        """Raise an unhandled error so the generic 500 path runs.

        Args:
            _request: Required by Starlette. Unused.

        Raises:
            RuntimeError: Always. The handler must turn it into a generic 500.
        """
        raise RuntimeError("boom")

    async def missing(_request: Request) -> JSONResponse:
        """Raise a domain 404 that must not use the unhandled handler.

        Args:
            _request: Required by Starlette. Unused.

        Raises:
            HTTPException: 404, which Starlette handles on its own.
        """
        raise HTTPException(status_code=404, detail="gone")

    async def ok(_request: Request) -> JSONResponse:
        """Return a body the tests ignore.

        Args:
            _request: Required by Starlette. Unused.

        Returns:
            A trivial JSON payload.
        """
        return JSONResponse({"ok": True})

    app.add_route("/boom", boom)
    app.add_route("/missing", missing)
    app.add_route("/ok", ok)
    app.add_middleware(CorrelationIdMiddleware)
    return app
