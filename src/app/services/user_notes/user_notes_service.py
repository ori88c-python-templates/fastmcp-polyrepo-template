"""User notes stored as a Redis list for one tenant and one user."""

from typing import Final

from structlog.typing import FilteringBoundLogger

from app.clients import RedisClient, create_redis_key
from app.metrics import UserNotesMetrics
from app.models.user_details import UserDetails

_NOTES_KEY_PREFIX: Final = "user_notes"
NOTES_PROMPT: Final = (
    "Record a note by calling the user-notes.add_note tool with the note text. "
    "Read the user-notes://notes resource for the notes already stored for this caller."
)


class UserNotesService:
    """Notes belonging to a tenant and a user, stored as a Redis list.

    The composition root constructs one instance and stores it on ``AppServices``.
    MCP primitives call these methods; they do not talk to Redis.

    This feature is a demonstration, so no traffic optimizations were added.
    A production ``add_note`` can take a keyed asyncio lock so one caller does
    not pile concurrent Redis writes on the same list. A production
    ``get_all_notes`` can keep a short TTL cache of that list. Those were left
    out on purpose.

    Args:
        redis: List store. Appends and reads go through ``RedisClient``.
        logger: Child logger whose ``context`` is ``UserNotesService``.
        metrics: Read and write counters, injected so this service does not own
            a process-wide Prometheus registry.
    """

    def __init__(
        self,
        redis: RedisClient,
        logger: FilteringBoundLogger,
        metrics: UserNotesMetrics,
    ) -> None:
        """Store dependencies. Does not talk to Redis.

        Args:
            redis: List store. Appends and reads go through ``RedisClient``.
            logger: Child logger whose ``context`` is ``UserNotesService``.
            metrics: Read and write counters.
        """
        self._redis: Final = redis
        self._logger: Final = logger
        self._metrics: Final = metrics

    async def add_note(self, text: str, user_details: UserDetails) -> None:
        """Append ``text`` to the caller's note list.

        Args:
            text: The note body. It is stored and not written to the log.
            user_details: Tenant and user the note belongs to.
        """
        await self._redis.append_list_item(
            create_redis_key(
                _NOTES_KEY_PREFIX,
                user_details.tenant_id,
                user_details.user_id,
            ),
            text,
        )
        self._metrics.writes_total.inc()
        self._logger.info("user_notes.added")

    async def get_all_notes(self, user_details: UserDetails) -> list[str]:
        """Return the caller's notes from oldest to newest.

        Args:
            user_details: Tenant and user whose notes are requested.

        Returns:
            The list stored for that caller. A missing key is an empty list.
        """
        self._metrics.reads_total.inc()
        notes = await self._redis.read_list(
            create_redis_key(
                _NOTES_KEY_PREFIX,
                user_details.tenant_id,
                user_details.user_id,
            ),
        )
        self._logger.info("user_notes.listed", count=len(notes))
        return notes

    async def get_prompt(self) -> str:
        """Return the fixed notes prompt. This does not read Redis.

        Returns:
            Instructions for recording a note and reading the notes resource.
        """
        return NOTES_PROMPT
