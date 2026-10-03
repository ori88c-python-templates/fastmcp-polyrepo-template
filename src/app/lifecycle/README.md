# lifecycle

The composition root. This is the only place that constructs dependencies and wires them to each
other, and the only place that knows the order resources must start and stop in.

## Table of Contents

- [Belongs here](#belongs-here)
- [Does not belong here](#does-not-belong-here)
- [Why a composition root](#why-a-composition-root)
- [Ordering](#ordering)
- [Registration](#registration)
- [Typed application state](#typed-application-state)

## Belongs here

- `LifecycleManager`, which builds the application (`create_app`) and installs
  process-wide logging (`install_process_logging`: `sys.excepthook`, the
  uvicorn error and access bridges, and the `fastmcp` logger bridge). Callers import
  `from app.lifecycle import LifecycleManager`.
- The startup and shutdown hooks that fill and later tear down `AppState`.

## Does not belong here

- Business logic, HTTP handlers, or anything that reads configuration from the environment.
  `LifecycleManager` is constructed with an already-validated `AppConfig`; it never builds one.

## Why a composition root

Every component declares its dependencies in its `__init__` and receives them. Something has to
actually construct that graph, and concentrating it in one place is what keeps it out of everywhere
else. Nothing outside this package calls a constructor for a client, a service, or a logger, which
is what makes the rest of the codebase free of global state and testable without patching.

### Why a class

`LifecycleManager` is a class rather than a set of functions because every construction step wants
the same two things, the configuration and a logger. It builds its own `LogManager` and child logger
in `__init__`, so each step can report what it is doing without that being threaded through six
signatures.

### Process hooks

`main.py` builds exactly one `LifecycleManager`, calls
`install_process_logging()`, then `create_app()`. `create_app` registers
`make_unhandled_http_exception_handler` on `Exception` with the same `uvicorn`
child the error bridge uses. The asyncio hook is installed for the lifespan of
the running loop. Access install is a no-op when
`LOGGER__ENABLE_UVICORN_ACCESS_LOGS` is false. The `fastmcp` bridge replaces
the Rich handlers FastMCP attached at import, so an unexpected tool, resource,
or prompt failure is structured JSON. The client still receives the masked
message.

## Ordering

Startup runs in topological order: a resource is opened only after everything it depends on is.
Shutdown runs the exact reverse, so a resource is closed only once everything that might still call
it is gone. Declare fields in `AppClients` in that same order, so the code reads as the contract.

Construction and connection are separate steps. `_build_app_state` runs before there is an event
loop, so anything needing one opens in `_init_by_topological_order` instead.

The log manager is flushed last. Everything else logs through it, so draining it earlier would
discard the records written during the rest of the shutdown.

## Registration

### Registrators

`create_app` builds a `FastMCP` server and calls registrators before `http_app()`.
Custom HTTP routes are `http_routes/register_<feature>.py`. MCP primitives are
`mcp_primitives/register_<feature>.py`. `create_app` does not decorate methods
itself. See `.cursor/rules/registrator-funcs.mdc`. Today that is
`register_k8s_probes(mcp)` and `register_user_notes_primitives(mcp, user_notes, loggers)`.
`http_app()` then returns the Starlette app. That call is
streamable HTTP with `stateless_http=True`. `ENABLE_SSE_STREAM_RESPONSE` maps to
`json_response=not ENABLE_SSE_STREAM_RESPONSE`. Redis startup is the FastMCP
lifespan, which `http_app` enters. Do not replace that Starlette lifespan and do
not call `mcp.run()`: `main` keeps `uvicorn.run` so the log bridges stay.

### Middleware order

Register middleware in `_add_middlewares_in_order`. Starlette wraps middleware in
reverse order — last added is outermost — see
[`middlewares/`](../middlewares/README.md). This package's order is
`PrometheusManager.add_middleware(app)` first (innermost), then
`CorrelationIdMiddleware` last (outermost). `add_metrics_router(app, config)`
mounts `GET /metrics` after that method. Gzip comes from `PrometheusConfig`.
Schema omission of `/metrics` is fixed in `PrometheusManager`. Each HTTP-aware custom
series is registered here so `PrometheusManager` does not catalog them.

Third-party `instrument(app)` / `setup(app)` helpers often call `add_middleware`
themselves. If that runs after `create_app()` returns, the library becomes outermost —
or sits outside this stack entirely if it wraps the app object. Register those
libraries in `_add_middlewares_in_order`, in the intended slot.

## Typed application state

Starlette keeps application state in an untyped bag whose attribute access returns `Any`. Reading it
directly would spread `Any` through every caller and silently switch off type checking.

`AppState` lives in [`state/`](../state/README.md), below this package so handlers can
call the accessors without importing the composition root. `LifecycleManager` is still
the only thing that constructs it. `get_app_state_from_app` is the single function in the
codebase that casts. Handlers should reach for `get_app_services`: handlers call services.
Readiness is the infrastructure exception and pings Redis directly. An MCP primitive
that needs a client belongs in a service instead.
