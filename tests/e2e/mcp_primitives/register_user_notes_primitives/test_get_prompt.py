"""The prompt does not depend on Redis or caller headers."""

from typing import Final

import mcp_types
import pytest

from app.services.user_notes.user_notes_service import NOTES_PROMPT
from tests.e2e.mcp_primitives.conftest import OpenMcpClient

pytestmark = pytest.mark.asyncio(loop_scope="session")

_GET_PROMPT: Final = "user-notes.get_prompt"


async def test_get_prompt_returns_the_constant(open_mcp_client: OpenMcpClient) -> None:
    """The prompt text is fixed, and the call needs no identity headers."""
    async with open_mcp_client({}) as mcp:
        result = await mcp.get_prompt(_GET_PROMPT)

    content = result.messages[0].content
    assert isinstance(content, mcp_types.TextContent)
    assert content.text == NOTES_PROMPT
