"""The prompt is a constant and does not use Redis."""

from unittest.mock import AsyncMock

from app.services import UserNotesService
from app.services.user_notes.user_notes_service import NOTES_PROMPT


async def test_get_prompt_returns_the_constant_without_redis(
    user_notes_service: UserNotesService,
    redis_client: AsyncMock,
) -> None:
    """The prompt text is fixed, and no list command runs."""
    assert await user_notes_service.get_prompt() == NOTES_PROMPT

    redis_client.append_list_item.assert_not_called()
    redis_client.read_list.assert_not_called()
