"""The routing contract kubelet is configured against."""

from http import HTTPStatus

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.routing import Route

from app.config import LIVEZ_ENDPOINT, READYZ_ENDPOINT

PROBE_PATHS = [LIVEZ_ENDPOINT, READYZ_ENDPOINT]


def _included_in_schema(app: Starlette, path: str) -> bool:
    """Return the schema flag of the single route mounted at ``path``.

    Args:
        app: Application whose route table is inspected.
        path: Exact path of the probe route.

    Returns:
        That route's ``include_in_schema`` flag.
    """
    matches = [
        route.include_in_schema
        for route in app.routes
        if isinstance(route, Route) and route.path == path
    ]
    (included,) = matches
    return included


async def test_liveness_is_served_without_an_api_prefix(probe_client: AsyncClient) -> None:
    """Liveness is exactly the path a manifest configures, with nothing in front.

    A prefix would couple kubelet's configuration to the MCP path, so moving the
    endpoint would silently stop every probe and roll the deployment.
    """
    response = await probe_client.get(LIVEZ_ENDPOINT)

    assert response.status_code == HTTPStatus.OK


async def test_readiness_is_served_without_an_api_prefix(ready_client: AsyncClient) -> None:
    """Readiness is exactly the path a manifest configures, with nothing in front."""
    response = await ready_client.get(READYZ_ENDPOINT)

    assert response.status_code == HTTPStatus.OK


@pytest.mark.parametrize("path", PROBE_PATHS)
async def test_probes_are_not_reachable_under_an_api_prefix(
    probe_client: AsyncClient, path: str
) -> None:
    """Nothing answers on a prefixed path, so the unprefixed one is not an alias."""
    response = await probe_client.get(f"/api/v1{path}")

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize("path", PROBE_PATHS)
async def test_probes_reject_methods_other_than_get(probe_client: AsyncClient, path: str) -> None:
    """Probes are reads. Anything else is a misconfiguration worth surfacing."""
    response = await probe_client.post(path)

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


@pytest.mark.parametrize("path", PROBE_PATHS)
def test_probes_are_included_in_schema(probe_app: Starlette, path: str) -> None:
    """Local and dev mark both probe routes for schema."""
    assert _included_in_schema(probe_app, path) is True


async def test_probes_hidden_from_schema_are_still_served(
    schema_hidden_probe_app: Starlette,
) -> None:
    """Staging and production omit kubelet paths from schema; kubelet still calls them."""
    for path in PROBE_PATHS:
        assert _included_in_schema(schema_hidden_probe_app, path) is False

    async with AsyncClient(
        transport=ASGITransport(app=schema_hidden_probe_app),
        base_url="http://probes.test",
    ) as client:
        for path in PROBE_PATHS:
            response = await client.get(path)
            assert response.status_code == HTTPStatus.OK
