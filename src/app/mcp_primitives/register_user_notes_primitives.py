"""Register the UserNotes tool, resource, and prompt."""

from dataclasses import dataclass

import mcp_types
from fastmcp import FastMCP
from fastmcp.dependencies import Depends
from structlog.typing import FilteringBoundLogger

from app.mcp_primitives.get_user_details import get_user_details
from app.models.user_details import UserDetails
from app.services import UserNotesService

_ADD_NOTE = "user-notes.add_note"
_ADD_NOTE_TITLE = "Add a note"
_ADD_NOTE_DESCRIPTION = "Record one note for the caller."
_GET_ALL_NOTES = "user-notes.get_all_notes"
_NOTES_TITLE = "List notes"
_NOTES_DESCRIPTION = "List the caller's notes, oldest first."
_NOTES_MIME_TYPE = "application/json"
_GET_PROMPT = "user-notes.get_prompt"
_GET_PROMPT_DESCRIPTION = "Return the instructions for recording and reading this caller's notes."
_NOTES_URI = "user-notes://notes"


@dataclass(frozen=True, slots=True)
class UserNotesMcpLoggers:
    """Child loggers for UserNotes primitives that log themselves.

    A typical tool, resource, or prompt designates the work to a service, and
    that service's logger is enough. Logging from the primitive is uncommon.
    This dataclass is a demonstration of how to pass primitive loggers when
    there is a real reason. A production feature may have no such fields.
    ``add_note`` logs the call; the resource and the prompt do not.

    Attributes:
        add_note: Child logger whose ``context`` is ``user-notes.add_note``.
    """

    add_note: FilteringBoundLogger


def register_user_notes_primitives(
    mcp: FastMCP,
    user_notes: UserNotesService,
    loggers: UserNotesMcpLoggers,
) -> None:
    """Register the UserNotes tool, resource, and prompt on ``mcp``.

    Call this before ``http_app``. The service and loggers are closed over.
    Caller identity arrives through ``Depends(get_user_details)``, not as a
    registrator argument.

    ``run_in_thread=False`` because ``UserNotesService`` does no blocking
    synchronous work. The decorator default ``True`` is for a blocking sync
    function. ``title`` is the host label. Tool annotations say the call
    appends a note: it writes, it does not destroy existing notes, it is not
    idempotent, and it does not leave this server's Redis. The notes resource
    is ``application/json``.

    Args:
        mcp: The server the composition root is building.
        user_notes: The process-wide notes service.
        loggers: Primitive loggers for the calls that log themselves.
    """

    @mcp.tool(
        name=_ADD_NOTE,
        title=_ADD_NOTE_TITLE,
        description=_ADD_NOTE_DESCRIPTION,
        annotations=mcp_types.ToolAnnotations(
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,
            open_world_hint=False,
        ),
        run_in_thread=False,
    )
    async def add_note(
        text: str,
        user_details: UserDetails = Depends(get_user_details),  # noqa: B008
    ) -> None:
        """Record one note for the caller.

        Args:
            text: The note body.
            user_details: Tenant and user from the inbound headers.
        """
        loggers.add_note.info("user_notes.add_note")
        await user_notes.add_note(text, user_details)

    @mcp.resource(
        _NOTES_URI,
        name=_GET_ALL_NOTES,
        title=_NOTES_TITLE,
        description=_NOTES_DESCRIPTION,
        mime_type=_NOTES_MIME_TYPE,
    )
    async def get_all_notes(
        user_details: UserDetails = Depends(get_user_details),  # noqa: B008
    ) -> list[str]:
        """List the caller's notes.

        Args:
            user_details: Tenant and user from the inbound headers.

        Returns:
            The notes stored for that caller, oldest first.
        """
        return await user_notes.get_all_notes(user_details)

    @mcp.prompt(name=_GET_PROMPT, description=_GET_PROMPT_DESCRIPTION)
    async def get_prompt() -> str:
        """Return the notes prompt.

        The decorator ``description`` is what the client lists. This text is
        for readers of the registrator. The body is the service constant.

        Returns:
            The fixed prompt from ``UserNotesService``.
        """
        return await user_notes.get_prompt()
