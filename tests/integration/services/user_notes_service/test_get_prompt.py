"""The prompt does not depend on Redis."""

from app.services import UserNotesService
from app.services.user_notes.user_notes_service import NOTES_PROMPT


async def test_get_prompt_returns_the_constant(
    user_notes_service: UserNotesService,
) -> None:
    """The prompt text is fixed."""
    assert await user_notes_service.get_prompt() == NOTES_PROMPT
