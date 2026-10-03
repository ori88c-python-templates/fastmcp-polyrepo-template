"""An unexpected tool error is logged in full and hidden from the client."""

import logging
from io import BytesIO

import mcp_types
from fastmcp import Client, FastMCP

from app.logger import LogManager, install_fastmcp_logging
from tests.unit.logger.log_manager.helpers import read_records

_ERROR_TEXT = "boom-secret"
_TOOL = "explode"


async def test_unhandled_tool_error_is_logged_and_masked(
    log_manager: LogManager,
    sink: BytesIO,
) -> None:
    """The client sees FastMCP's generic tool error. The sink has the traceback.

    Restores the ``fastmcp`` logger so later tests keep the handlers this
    process already had.
    """
    stdlib = logging.getLogger("fastmcp")
    previous_handlers = list(stdlib.handlers)
    previous_filters = list(stdlib.filters)
    previous_level = stdlib.level
    previous_propagate = stdlib.propagate
    try:
        install_fastmcp_logging(log_manager.get_child_logger("fastmcp"))
        mcp = FastMCP("mask-test", mask_error_details=True)

        @mcp.tool(name=_TOOL, run_in_thread=False)
        async def explode() -> None:
            """Raise an unexpected error.

            Raises:
                RuntimeError: Always. The client must not see its text.
            """
            raise RuntimeError(_ERROR_TEXT)

        async with Client(mcp) as client:
            result = await client.call_tool(_TOOL, {}, raise_on_error=False)

        assert result.is_error is True
        rendered = " ".join(
            block.text for block in result.content if isinstance(block, mcp_types.TextContent)
        )
        assert _ERROR_TEXT not in rendered
        assert _TOOL in rendered

        logged = [record for record in read_records(sink) if _ERROR_TEXT in str(record)]
        assert logged
        assert any(_TOOL in record["msg"] for record in logged)
    finally:
        stdlib.handlers = previous_handlers
        stdlib.filters = previous_filters
        stdlib.setLevel(previous_level)
        stdlib.propagate = previous_propagate
