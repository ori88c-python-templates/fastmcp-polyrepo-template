# state

Typed application state and the accessors that recover it from Starlette's untyped bag.

## Table of Contents

- [Belongs here](#belongs-here)
- [Does not belong here](#does-not-belong-here)
- [Why a package of its own](#why-a-package-of-its-own)
- [Request-scoped identity (when you add auth)](#request-scoped-identity-when-you-add-auth)

## Belongs here

- `AppState`, `AppClients`, and `AppServices`: the frozen container the composition
  root fills once and every request reads.
- The getters that take a `Request` or Starlette app and return a real type.
  Bag accessors (`get_app_state`, `get_app_services`) and later per-service
  getters all live in `app_state_getters.py`. Name later service getters
  `get_<use_case>_service`.

Callers outside this package import from [`__init__.py`](__init__.py):
`from app.state import AppState, get_app_services`. Modules inside it
still import siblings by module path (`from app.state.app_state import AppState`);
a getter importing `from app.state import AppState` would cycle.

## Does not belong here

- Constructing clients or services. `LifecycleManager` is the composition root; this
  package only types and retrieves what that root already built.
- Business logic or HTTP handlers.

## Why a package of its own

Handlers call the getters. The getters cannot live in `lifecycle/`: that package sits *above*
`http_routes/` and `mcp_primitives/`, so a registration module importing it would be an upward import and a cycle once the
composition root imported the registration function.

This package sits below the HTTP layer and above `services/`, which is the one place
that can know Starlette, `AppServices`, and `AppClients` without either layering
violation. `get_app_state_from_app` remains the only cast in the codebase.

## Request-scoped identity (when you add auth)

Auth is not shipped. Identity is a method argument. The shipped notes service
takes `UserDetails`. A later bearer-token check builds that object, or the fields
the method already takes. Do not put a credential on a service `__init__`. Do not
use a session id. Accessors here call `get_app_services()`, never
`get_app_state().clients`. Probes and `GET /metrics` stay out. See the root README
Authentication section.

