# clients

Clients for external resources: the application's data access layer.

## Table of Contents

- [Belongs here](#belongs-here)
- [Does not belong here](#does-not-belong-here)
- [Dependency injection](#dependency-injection)

## Belongs here

- One client class per resource, in a file named after that resource.
- Connection pools, query helpers, and the thin wrappers around Redis and third-party APIs.

Callers outside this package import from [`__init__.py`](__init__.py):
`from app.clients import RedisClient, create_redis_key`. `create_redis_key` builds a
length-prefixed key so a colon inside one part cannot merge with the next.
`RedisClient` is the pool. Modules inside a client package still import
siblings by module path.

## Does not belong here

- Business logic. A client executes a command against one resource; it does not decide whether
  that command should run. That belongs in a service.
- HTTP. A client never imports FastMCP, FastAPI, or Starlette. A Redis client that knows about request
  objects is the canonical layering violation.
- Configuration loading. A client is constructed with an already-validated config model; it never
  reads the environment.

## Dependency injection

A client declares its config and a child logger in its `__init__`. The composition root constructs
it once, starts it in topological order, and stores it on `AppClients`. A client never constructs
another client, reaches for a global, or builds its own logger.
