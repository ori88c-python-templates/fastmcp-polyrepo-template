"""Tenant and user ids are on logs inside get_user_details and gone after it."""

from io import BytesIO

from app.logger import LogManager
from app.mcp_primitives import get_user_details
from tests.unit.logger.log_manager.helpers import read_records

_INSIDE = "user_details.inside"
_OUTSIDE = "user_details.outside"


async def test_user_ids_are_bound_only_inside_get_user_details(
    log_manager: LogManager,
    sink: BytesIO,
) -> None:
    """A log inside the call carries both ids. A log after exit does not."""
    logger = log_manager.get_child_logger("user-details")
    async with get_user_details({"x-tenant-id": "tenant-a", "x-user-id": "user-1"}):
        logger.info(_INSIDE)
    logger.info(_OUTSIDE)

    inside, outside = read_records(sink)
    assert inside["msg"] == _INSIDE
    assert inside["tenant_id"] == "tenant-a"
    assert inside["user_id"] == "user-1"
    assert outside["msg"] == _OUTSIDE
    assert "tenant_id" not in outside
    assert "user_id" not in outside
