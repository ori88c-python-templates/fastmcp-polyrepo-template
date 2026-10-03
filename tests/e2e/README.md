# e2e

HTTP through the real application: `LifecycleManager`, registered features, middleware, and
throwaway Redis.

## Table of Contents

- [Belongs here](#belongs-here)
- [Does not belong here](#does-not-belong-here)

## Belongs here

### In-process requests

Requests go in-process, not through a uvicorn subprocess. Lifespan starts the Redis
client once for the session.

### Shared Redis

Throwaway Redis is the session fixture `throwaway_stores` in
[`../conftest.py`](../conftest.py) ([`throwaway_stores.py`](../throwaway_stores.py)).
Integration tests share that container helper. It stays in the root conftest:
integration and e2e are sibling directories, and pytest 9 rejects `pytest_plugins`
in a nested conftest. The fixture is not autouse, and the container module is
imported only when a test requests it, so `pytest tests/unit` starts no container.
`AppConfig` is built from that Redis config so Compose `.env` is never the address.
The session fixture `app_config` is what `app` and the MCP client both use, so the
client URL stays on `MCP_PATH`.

### Test layout

Layout mirrors `src/app/http_routes/` and `src/app/mcp_primitives/`. Probe coverage lives in
`tests/e2e/http_routes/register_k8s_probes/` and uses `client`. User-notes coverage lives in
`tests/e2e/mcp_primitives/register_user_notes_primitives/` and uses `open_mcp_client`
from [`mcp_primitives/conftest.py`](mcp_primitives/conftest.py). That factory speaks
streamable HTTP through `httpx2` against the same ASGI app. A later feature is
`tests/e2e/http_routes/<feature>/` or `tests/e2e/mcp_primitives/<feature>/`.

### One session app

Reuse `client` or `open_mcp_client`; do not start another app (the process-wide
Prometheus registry cannot register the same series twice). Each test module sets
`pytestmark = pytest.mark.asyncio(loop_scope="session")` so the calls use the same
event loop as the session-scoped lifespan.

## Does not belong here

Docker Desktop must be running. If the daemon is down, these tests skip.
Service-only tests belong in [`../integration/`](../integration/README.md).
In-process tests (buffers, temp files, `AsyncMock`) belong in
[`../unit/`](../unit/README.md).
