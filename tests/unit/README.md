# unit

In-process tests only.

## Table of Contents

- [Belongs here](#belongs-here)
- [Does not belong here](#does-not-belong-here)

## Belongs here

Dependencies are passed in: a `BytesIO` for the log manager, an `AsyncMock` for a client the
handler does not need to exercise, a temp file for encoding checks. Injecting a dependency is
fine: a buffer, a temp file, an in-memory implementation, or an `AsyncMock` constructed and
handed to `AppState`. That is dependency injection, not patching.

Layout mirrors `src/app/`: one directory per package, then one directory per component
under test, then one file per feature.

```
http_routes/     register_k8s_probes, get_http_route_logger
mcp_primitives/  get_user_details
registrator_funcs/  registration calls stay in register_*.py
middlewares/     correlation_id_middleware, unhandled_http_exception_handler
prometheus/      HTTP metrics wiring (the package is the component)
logger/          log_manager, asyncio_exception_handler, sys_excepthook,
                 uvicorn_access_log_handler, uvicorn_error_log_handler,
                 uvicorn_asgi_exception_filter
config/          app_config, logger_config, redis_config
distribution/    installed_app_version
clients/         redis_client
services/        user_notes_service
```

Service unit tests mock Redis and use a private Prometheus registry.

## Does not belong here

A unit test never opens a socket to Redis, never starts the real application lifespan
against that server, and never starts Docker. `unittest.mock.patch` and `monkeypatch`
are still forbidden.
