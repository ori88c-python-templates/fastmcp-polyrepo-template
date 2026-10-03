# integration

Tests that exercise a **service** against real Redis.

[`services/user_notes_service/`](services/user_notes_service/) covers
`UserNotesService` against the session Redis. A later service reuses
`redis_client` from [`conftest.py`](conftest.py) rather than starting its own
container.

## Table of Contents

- [Belongs here](#belongs-here)
- [Isolation](#isolation)
- [Does not belong here](#does-not-belong-here)

## Belongs here

Testcontainers starts throwaway `redis:7-alpine` (the same image as local Compose), on
a random host port so it cannot collide with Compose. That startup is the session
fixture `throwaway_stores` in [`../conftest.py`](../conftest.py)
([`throwaway_stores.py`](../throwaway_stores.py)), shared with e2e.
[`conftest.py`](conftest.py) is fixtures only.

Construct the service with the real `RedisClient` from [`conftest.py`](conftest.py).
A later service should reuse that fixture rather than start its own container.

## Isolation

Redis `FLUSHDB` runs in the integration conftest before every test, so a later service
does not inherit keys.

## Does not belong here

This is not HTTP. Registrators, middleware, and `LifecycleManager` stay out.
Docker Desktop must be running. If the daemon is down, these tests skip.
In-process tests (buffers, temp files, `AsyncMock`) belong in
[`../unit/`](../unit/README.md). Cross-layer HTTP belongs in
[`../e2e/`](../e2e/README.md).
