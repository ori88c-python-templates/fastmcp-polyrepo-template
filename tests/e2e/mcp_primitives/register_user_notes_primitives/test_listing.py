"""The notes tool and resource advertise their catalog fields."""

from typing import Final

import mcp_types
import pytest

from app.config import TENANT_ID_HEADER, USER_ID_HEADER
from tests.e2e.mcp_primitives.conftest import OpenMcpClient

pytestmark = pytest.mark.asyncio(loop_scope="session")

_ADD_NOTE: Final = "user-notes.add_note"
_ADD_NOTE_TITLE: Final = "Add a note"
_NOTES_TITLE: Final = "List notes"
_NOTES_MIME_TYPE: Final = "application/json"
_NOTES_URI: Final = "user-notes://notes"
_USER_A: Final = {TENANT_ID_HEADER: "tenant-a", USER_ID_HEADER: "user-1"}
_ADD_NOTE_DESCRIPTION: Final = "Record one note for the caller."
_NOTES_DESCRIPTION: Final = "List the caller's notes, oldest first."
_GET_PROMPT: Final = "user-notes.get_prompt"
_GET_PROMPT_DESCRIPTION: Final = (
    "Return the instructions for recording and reading this caller's notes."
)
_STALE_DESCRIPTION: Final = (
    "Empty until persistence exists",
    "Empty until it is written",
)


async def test_notes_catalog_advertises_title_hints_and_json(
    open_mcp_client: OpenMcpClient,
) -> None:
    """The host sees a write that appends, and a JSON notes resource."""
    async with open_mcp_client(_USER_A) as mcp:
        tool = next(item for item in await mcp.list_tools() if item.name == _ADD_NOTE)
        assert tool.title == _ADD_NOTE_TITLE
        assert tool.description == _ADD_NOTE_DESCRIPTION
        hints = tool.annotations
        assert hints is not None
        assert hints.read_only_hint is False
        assert hints.destructive_hint is False
        assert hints.idempotent_hint is False
        assert hints.open_world_hint is False

        resource = next(item for item in await mcp.list_resources() if str(item.uri) == _NOTES_URI)
        assert resource.title == _NOTES_TITLE
        assert resource.description == _NOTES_DESCRIPTION
        assert resource.mime_type == _NOTES_MIME_TYPE

        content = (await mcp.read_resource(_NOTES_URI))[0]
        assert isinstance(content, mcp_types.TextResourceContents)
        assert content.mime_type == _NOTES_MIME_TYPE

        prompt = next(item for item in await mcp.list_prompts() if item.name == _GET_PROMPT)
        assert prompt.description == _GET_PROMPT_DESCRIPTION

        published = (tool.description, resource.description, prompt.description)
        for text in published:
            assert text is not None
            for stale in _STALE_DESCRIPTION:
                assert stale not in text
