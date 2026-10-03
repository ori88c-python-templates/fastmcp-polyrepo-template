# http_routes

Registration of custom HTTP routes. A registrator here is `register_<feature>.py`,
the only place a feature may call `custom_route`. MCP primitives live in
[`mcp_primitives/`](../mcp_primitives/README.md), not here. The two packages do
not import each other. See `.cursor/rules/registrator-funcs.mdc`.

## Table of Contents

- [Belongs here](#belongs-here)
- [Does not belong here](#does-not-belong-here)
- [Dependency injection](#dependency-injection)
- [Schema](#schema)
- [Unhandled errors](#unhandled-errors)
- [Sibling independence](#sibling-independence)

## Belongs here

- One `register_<feature>` function per feature, in a file named after that function
  (`register_k8s_probes.py`). Nest a feature only when that feature grows a second module.
- Handlers for those registrations. A custom HTTP handler takes a Starlette `Request`
  and returns a `Response`.

Callers outside this package import from [`__init__.py`](__init__.py):
`from app.http_routes import register_k8s_probes, get_http_route_logger`. A registration
module still imports `get_http_route_logger` from `get_http_route_logger.py` by module
path; importing `from app.http_routes import get_http_route_logger` inside that module
would cycle.

The composition root calls `register_k8s_probes(mcp)` before `http_app()`, because
custom routes are copied onto the Starlette app at that moment.

## Does not belong here

- MCP tools, resources, prompts, completions, or other primitives. Those are
  `mcp_primitives/`.
- Business logic. A handler should validate its input, call a service, and shape the result. If a
  handler is growing branches, the logic belongs in a service.
- Direct database or cache access. Handlers talk to services; services talk to resources.
  Readiness is the infrastructure exception: it pings Redis because a probe must not
  grow a service, and kubelet is the only caller. An MCP primitive must not copy that
  ping; it calls a service on `AppServices`.
- Request and response schemas — those live in [`models/`](../models/README.md).

## Dependency injection

Handlers read [`state/`](../state/README.md) accessors off the request. A handler never
constructs a service, reaches for a global, or builds its own logger.

If a custom HTTP route logs, it calls [`get_http_route_logger`](get_http_route_logger.py).
That is the only way an HTTP handler may log: no `get_child_logger` inside the function,
no module-level logger, no grabbing `LogManager` off state except through that helper.
MCP primitives do not use it; they log through an injected child logger.
Services still receive a constructor-injected logger named after the service; the same
request can therefore emit two `context` values with one `correlation_id`.

Liveness stays dependency-free and does not log. Readiness reads Redis from
application state and logs through `get_http_route_logger`. Probe paths come from
[`config/app_consts.py`](../config/app_consts.py).

## Schema

`custom_route(..., name=, include_in_schema=)` is the registration. `name=` is what
`get_http_route_logger` copies into the log `context`. The handler's Google docstring
stays in the code. `include_in_schema` sets Starlette's route flag. This process does
not serve `/docs` or an OpenAPI document.

Kubernetes probes stay mounted for kubelet in every environment. They are omitted
from schema when `ENV` is `staging` or `prod`.

## Unhandled errors

Anything the handler does not turn into an explicit error response becomes Starlette's
generic `500 Internal Server Error`. Do not put driver messages in the body.

## Sibling independence

`http_routes/`, `mcp_primitives/`, `middlewares/`, and `prometheus/` sit in the same
layer and must not import each other. A shared path or header name moves down, not sideways.
