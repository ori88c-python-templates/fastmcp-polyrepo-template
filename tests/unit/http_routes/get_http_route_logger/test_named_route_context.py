"""The injected HTTP route logger binds ``context`` to the explicit route name."""

from io import BytesIO

from httpx import AsyncClient

from app.config import READYZ_ENDPOINT
from tests.unit.logger.log_manager.helpers import read_records


async def test_readiness_emits_the_explicit_route_name_as_context(
    client: AsyncClient,
    sink: BytesIO,
) -> None:
    """Readiness logs with ``context`` equal to the decorator's ``name=``."""
    await client.get(READYZ_ENDPOINT)

    (record,) = read_records(sink)
    assert record["context"] == "k8s-probe-router.ready"
    assert record["msg"] == "readiness.probe"
