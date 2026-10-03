"""Notes persist in Redis in insertion order, one list per caller."""

import json
from typing import Final, cast

import mcp_types
import pytest

from app.config import TENANT_ID_HEADER, USER_ID_HEADER
from tests.e2e.mcp_primitives.conftest import OpenMcpClient

pytestmark = pytest.mark.asyncio(loop_scope="session")

_ADD_NOTE: Final = "user-notes.add_note"
_NOTES_URI: Final = "user-notes://notes"
_USER_A: Final = {TENANT_ID_HEADER: "tenant-a", USER_ID_HEADER: "user-1"}
_USER_B: Final = {TENANT_ID_HEADER: "tenant-b", USER_ID_HEADER: "user-2"}


def _note_list(
    contents: list[mcp_types.TextResourceContents | mcp_types.BlobResourceContents],
) -> list[str]:
    """Decode the notes resource body.

    Args:
        contents: Blocks returned by ``read_resource``.

    Returns:
        The note strings, oldest first.
    """
    content = contents[0]
    assert isinstance(content, mcp_types.TextResourceContents)
    parsed = cast("list[object]", json.loads(content.text))
    notes: list[str] = []
    for item in parsed:
        assert isinstance(item, str)
        notes.append(item)
    return notes


async def test_two_adds_are_returned_oldest_first(open_mcp_client: OpenMcpClient) -> None:
    """RPUSH keeps insertion order for a later resource read."""
    async with open_mcp_client(_USER_A) as mcp:
        first = await mcp.call_tool(_ADD_NOTE, {"text": "first"})
        second = await mcp.call_tool(_ADD_NOTE, {"text": "second"})

        assert first.is_error is False
        assert second.is_error is False
        assert _note_list(await mcp.read_resource(_NOTES_URI)) == ["first", "second"]


async def test_another_caller_does_not_see_the_notes(open_mcp_client: OpenMcpClient) -> None:
    """The Redis key includes both tenant and user, so lists stay separate."""
    async with open_mcp_client(_USER_A) as owner:
        added = await owner.call_tool(_ADD_NOTE, {"text": "secret"})
        assert added.is_error is False

    async with open_mcp_client(_USER_B) as other:
        assert _note_list(await other.read_resource(_NOTES_URI)) == []


async def test_get_all_notes_on_an_empty_list_returns_nothing(
    open_mcp_client: OpenMcpClient,
) -> None:
    """A caller with no notes gets an empty list, not an error."""
    async with open_mcp_client(_USER_A) as mcp:
        assert _note_list(await mcp.read_resource(_NOTES_URI)) == []
