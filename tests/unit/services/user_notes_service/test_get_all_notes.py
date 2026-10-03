"""Reading notes returns the Redis list and does not write."""

from typing import Final
from unittest.mock import AsyncMock

from app.clients import create_redis_key
from app.models.user_details import UserDetails
from app.services import UserNotesService

_USER_A_DETAILS: Final = UserDetails(tenant_id="tenant-a", user_id="user-1")
_USER_A_NOTES_KEY: Final = create_redis_key(
    "user_notes",
    _USER_A_DETAILS.tenant_id,
    _USER_A_DETAILS.user_id,
)


async def test_get_all_notes_returns_the_list_without_pushing(
    user_notes_service: UserNotesService,
    redis_client: AsyncMock,
) -> None:
    """The stored list is the result, oldest first, and nothing is appended."""
    redis_client.read_list.return_value = ["first", "second"]

    notes = await user_notes_service.get_all_notes(_USER_A_DETAILS)

    assert notes == ["first", "second"]
    redis_client.read_list.assert_awaited_once_with(_USER_A_NOTES_KEY)
    redis_client.append_list_item.assert_not_called()
