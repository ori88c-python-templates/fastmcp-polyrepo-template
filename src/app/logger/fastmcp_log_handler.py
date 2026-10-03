"""Bridge the ``fastmcp`` stdlib logger into a structured ``LogManager`` child.

Importing FastMCP calls ``configure_logging()``, which attaches Rich handlers
and sets ``propagate = False``. Tool, resource, and prompt failures are logged
there. This bridge replaces those handlers so the same records are JSON.
"""

import logging
from typing import Final

from structlog.typing import FilteringBoundLogger

from app.logger.uvicorn_log_handler import UvicornLogHandler

_FASTMCP_LOGGER: Final = "fastmcp"


def install_fastmcp_logging(logger: FilteringBoundLogger) -> None:
    """Replace FastMCP's stderr handlers with a structured handler.

    ``propagate`` stays off so root / lastResort does not also print the line.
    The level is INFO: unexpected primitive failures are logged at ERROR.

    Args:
        logger: Child logger named ``fastmcp``. Closed over by the handler.
    """
    fastmcp_logger = logging.getLogger(_FASTMCP_LOGGER)
    for handler in fastmcp_logger.handlers[:]:
        fastmcp_logger.removeHandler(handler)
    fastmcp_logger.addHandler(UvicornLogHandler(logger))
    fastmcp_logger.setLevel(logging.INFO)
    fastmcp_logger.propagate = False
