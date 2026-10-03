"""Notes persist in Redis in insertion order, one list per caller."""

from typing import Final

from app.models.user_details import UserDetails
from app.services import UserNotesService

_USER_A_DETAILS: Final = UserDetails(tenant_id="tenant-a", user_id="user-1")
_USER_B_DETAILS: Final = UserDetails(tenant_id="tenant-b", user_id="user-2")


async def test_two_adds_are_returned_oldest_first(
    user_notes_service: UserNotesService,
) -> None:
    """RPUSH keeps insertion order for a later read."""
    await user_notes_service.add_note("first", _USER_A_DETAILS)
    await user_notes_service.add_note("second", _USER_A_DETAILS)

    assert await user_notes_service.get_all_notes(_USER_A_DETAILS) == ["first", "second"]


async def test_another_caller_does_not_see_the_notes(
    user_notes_service: UserNotesService,
) -> None:
    """The Redis key includes both tenant and user, so lists stay separate."""
    await user_notes_service.add_note("secret", _USER_A_DETAILS)

    assert await user_notes_service.get_all_notes(_USER_B_DETAILS) == []


async def test_get_all_notes_on_an_empty_list_returns_nothing(
    user_notes_service: UserNotesService,
) -> None:
    """A caller with no notes gets an empty list, not an error."""
    assert await user_notes_service.get_all_notes(_USER_A_DETAILS) == []
