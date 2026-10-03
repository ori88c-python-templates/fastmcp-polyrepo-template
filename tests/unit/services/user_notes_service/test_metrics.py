"""Business counters increment when the matching use case runs."""

from typing import Final
from unittest.mock import AsyncMock

from prometheus_client import CollectorRegistry, generate_latest

from app.models.user_details import UserDetails
from app.services import UserNotesService

_USER_A_DETAILS: Final = UserDetails(tenant_id="tenant-a", user_id="user-1")


async def test_get_all_notes_increments_reads_total(
    user_notes_service: UserNotesService,
    redis_client: AsyncMock,
    collector_registry: CollectorRegistry,
) -> None:
    """A read is observable as scrape text on the service's registry."""
    redis_client.read_list.return_value = []

    await user_notes_service.get_all_notes(_USER_A_DETAILS)

    body = generate_latest(collector_registry).decode()
    assert "user_notes_reads_total 1.0" in body


async def test_add_note_increments_writes_total(
    user_notes_service: UserNotesService,
    collector_registry: CollectorRegistry,
) -> None:
    """A pushed note is observable as scrape text on the service's registry."""
    await user_notes_service.add_note("hello", _USER_A_DETAILS)

    body = generate_latest(collector_registry).decode()
    assert "user_notes_writes_total 1.0" in body


async def test_get_prompt_does_not_increment_note_counters(
    user_notes_service: UserNotesService,
    collector_registry: CollectorRegistry,
) -> None:
    """The prompt is not a Redis read or write."""
    await user_notes_service.get_prompt()

    body = generate_latest(collector_registry).decode()
    assert "user_notes_reads_total 0.0" in body
    assert "user_notes_writes_total 0.0" in body
