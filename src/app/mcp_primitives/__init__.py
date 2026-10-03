"""MCP primitive registration."""

from app.mcp_primitives.get_user_details import get_user_details
from app.mcp_primitives.register_user_notes_primitives import (
    UserNotesMcpLoggers,
    register_user_notes_primitives,
)

__all__ = [
    "UserNotesMcpLoggers",
    "get_user_details",
    "register_user_notes_primitives",
]
