"""Appending a note pushes it onto that caller's Redis list."""

from typing import Final
from unittest.mock import AsyncMock

from app.clients import create_redis_key
from app.models.user_details import UserDetails
from app.services import UserNotesService

_USER_A_DETAILS: Final = UserDetails(tenant_id="tenant-a", user_id="user-1")
_USER_B_DETAILS: Final = UserDetails(tenant_id="tenant-b", user_id="user-2")
_USER_A_NOTES_KEY: Final = create_redis_key(
    "user_notes",
    _USER_A_DETAILS.tenant_id,
    _USER_A_DETAILS.user_id,
)
_USER_B_NOTES_KEY: Final = create_redis_key(
    "user_notes",
    _USER_B_DETAILS.tenant_id,
    _USER_B_DETAILS.user_id,
)


async def test_add_note_pushes_the_text_onto_the_caller_list(
    user_notes_service: UserNotesService,
    redis_client: AsyncMock,
) -> None:
    """The note is the appended item, and the key names that tenant and user."""
    await user_notes_service.add_note("hello", _USER_A_DETAILS)

    redis_client.append_list_item.assert_awaited_once_with(_USER_A_NOTES_KEY, "hello")


async def test_add_note_uses_a_different_key_for_another_caller(
    user_notes_service: UserNotesService,
    redis_client: AsyncMock,
) -> None:
    """Two callers do not share a list."""
    await user_notes_service.add_note("theirs", _USER_B_DETAILS)

    redis_client.append_list_item.assert_awaited_once_with(_USER_B_NOTES_KEY, "theirs")
