"""Missing caller headers become a masked protocol error."""

from typing import Final

import mcp_types
import pytest
from fastmcp.client.client import CallToolResult
from mcp import MCPError

from tests.e2e.mcp_primitives.conftest import OpenMcpClient

pytestmark = pytest.mark.asyncio(loop_scope="session")

_ADD_NOTE: Final = "user-notes.add_note"
_NOTES_URI: Final = "user-notes://notes"
_NO_CALLER: Final[dict[str, str]] = {}


def _error_text(result: CallToolResult) -> str:
    """Join text blocks on a tool error result.

    Args:
        result: The value from ``call_tool(..., raise_on_error=False)``.

    Returns:
        The text the client would show.
    """
    return " ".join(
        block.text for block in result.content if isinstance(block, mcp_types.TextContent)
    )


async def test_add_note_without_caller_headers_is_masked(
    open_mcp_client: OpenMcpClient,
) -> None:
    """The tool fails, and the client does not receive a traceback."""
    async with open_mcp_client(_NO_CALLER) as mcp:
        result = await mcp.call_tool(_ADD_NOTE, {"text": "orphan"}, raise_on_error=False)

    rendered = _error_text(result)
    assert result.is_error is True
    assert "Traceback" not in rendered
    assert "ValidationError" not in rendered


async def test_read_resource_without_caller_headers_is_masked(
    open_mcp_client: OpenMcpClient,
) -> None:
    """The resource fails, and the client does not receive a traceback."""
    async with open_mcp_client(_NO_CALLER) as mcp:
        with pytest.raises(MCPError) as caught:
            await mcp.read_resource(_NOTES_URI)

    rendered = str(caught.value)
    assert "Traceback" not in rendered
    assert "ValidationError" not in rendered
