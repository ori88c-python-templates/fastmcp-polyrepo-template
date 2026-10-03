# middlewares

ASGI middleware: the other half of the HTTP layer, wrapping every request before it reaches
a route.

## Table of Contents

- [Belongs here](#belongs-here)
- [Does not belong here](#does-not-belong-here)
- [Registration](#registration)
- [Authentication](#authentication)
- [Sibling independence](#sibling-independence)

## Belongs here

- One middleware class per concern, in a file named after that concern.
- Cross-cutting HTTP behaviour that an MCP HTTP server actually needs: correlation ids,
  and later a uniform 401 if a clone cannot do that in the handler. Authentication in
  this template is resolved in the handler and passed into the service method
  (see below).

Callers outside this package import from [`__init__.py`](__init__.py):
`from app.middlewares import CorrelationIdMiddleware, make_unhandled_http_exception_handler`. A
middleware module still imports siblings by module path.

`CorrelationIdMiddleware` is a raw ASGI wrapper (not `BaseHTTPMiddleware`). It binds
`correlation_id` with `structlog.contextvars.bound_contextvars` for the request, stores
the same id on `request.state`, accepts
`X-Request-ID` or `X-Correlation-ID` inbound, and always returns `X-Request-ID`. Header
names come from [`config/app_consts.py`](../config/app_consts.py). It ignores non-HTTP
scopes. FastMCP's own spans and the JSON-RPC id do not cover probes or `/metrics`, so
this middleware stays.

`make_unhandled_http_exception_handler` is Starlette's `Exception` handler for
custom HTTP routes only: probes, `/metrics`, and other `custom_route` handlers.
It logs through a `uvicorn` child logger and returns Starlette's generic
`500 Internal Server Error`. It is not middleware; `LifecycleManager.create_app`
registers it with `add_exception_handler`. A raised tool, resource, or prompt
never reaches it. FastMCP catches that exception, `mask_error_details=True`
hides the text from the client, and `install_process_logging` bridges the
`fastmcp` logger so the traceback is structured JSON.

HTTP Prometheus (`add_middleware`, `add_metrics_router`, HTTP-aware series) lives in
[`prometheus/`](../prometheus/README.md), a sibling of this package. Collectors that
services increment live in [`metrics/`](../metrics/README.md).

## Does not belong here

- Business logic. Middleware inspects or annotates a request; it does not decide what the request
  means. That belongs in a service.
- Direct database or cache access. Middleware talks to services when it needs dependencies; it
  never reaches for a client.
- Browser document headers (CSP, framing, HSTS). This process returns JSON and SSE, not HTML.
- Knowledge of which features exist. Middleware wraps the whole application. If a path must be
  exempted (skipping auth for `/livez`), the constant lives in
  [`config/app_consts.py`](../config/app_consts.py), not in a registration function.

## Registration

Middleware is constructed by `LifecycleManager` and registered in `_add_middlewares_in_order`.
Starlette wraps middleware in reverse registration order, so the last one added is outermost.
A middleware never installs itself.

A library's `instrument(app)` / `setup(app)` often calls `add_middleware` at the call
site. `PrometheusManager.add_middleware(app)` is the usual example: it is registered
**first** in `_add_middlewares_in_order` (innermost of the two).
`add_metrics_router` mounts `GET /metrics` and is called after that method, once
`http_app()` has returned.

## Authentication

The handler passes `UserDetails` into the service method. The shipped notes
primitive does that via `Depends(get_user_details)`. A later check is a bearer
token built into that object, not a session id. Probes and `/metrics` stay
unauthenticated. See the root README.

If a clone needs a uniform 401 before routing, add an ASGI wrapper here and register
it only in `LifecycleManager._add_middlewares_in_order`. Register it **before**
`CorrelationIdMiddleware` (that class stays last, so it stays outermost and every
log line — including a 401 — still has `correlation_id`). Exempt `LIVEZ_ENDPOINT`,
`READYZ_ENDPOINT`, and `METRICS_ENDPOINT` from
[`app_consts.py`](../config/app_consts.py); do not import registrator modules to decide —
`middlewares/`, `http_routes/`, and `mcp_primitives/` are siblings, so that import is a cycle.
The wrapper talks to a service, never to `RedisClient`. Do not
`instrument(app)` / wrap the app in `main`.

## Sibling independence

`http_routes/`, `mcp_primitives/`, `middlewares/`, and `prometheus/` sit in the same layer and must not import each
other. A shared path or header name moves down, not sideways.
