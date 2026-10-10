# FastMCP Polyrepo Template

[![CI](https://github.com/ori88c-python-templates/fastmcp-polyrepo-template/actions/workflows/ci.yml/badge.svg)](https://github.com/ori88c-python-templates/fastmcp-polyrepo-template/actions/workflows/ci.yml)
[![Audit](https://github.com/ori88c-python-templates/fastmcp-polyrepo-template/actions/workflows/audit.yml/badge.svg)](https://github.com/ori88c-python-templates/fastmcp-polyrepo-template/actions/workflows/audit.yml)

Production-grade FastMCP template built around **dependency injection** and **zero global state**.
A composition root wires clients, services, and loggers so tests inject dependencies instead of monkeypatching; Cursor rules keep AI edits copying this architecture. Layered import DAG, Testcontainers, Prometheus, and Kubernetes probes included.

## Table of Contents

- [Highlights](#highlights)
- [Why this template](#why-this-template)
- [Architecture](#architecture)
- [Layout](#layout)
- [Configuration](#configuration)
- [Logging](#logging)
- [Demonstrative Feature - User Notes](#demonstrative-feature---user-notes)
- [Running locally](#running-locally)
- [Container image](#container-image)
- [Production deploy](#production-deploy)
- [Testing](#testing)
- [Linting and type checking](#linting-and-type-checking)
- [Pre-commit hooks](#pre-commit-hooks)
- [CI](#ci)
- [Authentication](#authentication)

## Highlights

- **Dependency injection, zero global state** 🧩: Every component takes dependencies in `__init__`; `LifecycleManager` (the composition root) constructs the clients, services, and loggers and wires them — `main.py` only builds `AppConfig` and that manager. No module-level config, logger, or client, so tests inject dependencies instead of monkeypatching or process-wide setup.
- **Three-layer import DAG, enforced** 🧭: The protocol surface (`http_routes` / `mcp_primitives` / `middlewares` / `prometheus`), services, and clients stay loosely coupled so you can test a service without FastMCP and a client without a registrator. Packages import downward only; `lint-imports` fails cycles and FastMCP leaking into services or clients.
- **Sample vertical slice** 🚩: `UserNotesService` plus its tool, resource, and prompt, Prometheus series, and matching integration and e2e tests. Copy that pattern for the next feature.
- **Nested Pydantic config** ⚙️: `AppConfig` composes resource-specific models (`redis`, `logger`, `prometheus`, …). Invalid config fails at startup, not on the first request.
- **Structured JSON logging** 📡: Every line carries prod-grade fields (`app`, `instance`, `env`, `app.version`, `correlation_id`). Each component gets a named child logger with its own `context`, so you can filter easily — with grep, or with observability tools such as Groundcover, Grafana, and Datadog.
- **Unit, integration, and e2e from day 1** 🧪: `pytest` is wired for all three: in-process units, Testcontainers against real Redis, and the real app through `LifecycleManager`. The notes slice is covered at each layer.
- **Cursor rules that keep the conventions** 🤖: Checked-in [`.cursor/rules`](.cursor/rules) encode layers, logging, tests, and metrics so AI-assisted edits copy this architecture instead of inventing a new one.
- **Production-shaped ops** 🚢: Non-root multi-stage image, Kubernetes liveness and readiness probes (`GET /livez`, `GET /readyz`), Prometheus scrape (`GET /metrics`), and GitHub Actions CI. HTTP-aware Prometheus series live in `prometheus/`; the notes counters live in `metrics/`.
- **Supply-chain hygiene** 🔒: SHA-pinned Actions, weekly Dependabot for the `uv` lockfile and GitHub Actions, and a separate `uv audit` workflow on push/PR plus a weekly schedule so a CVE published while `main` is idle still fails the Audit badge.

## Why this template

Unlike opinionated application frameworks such as NestJS, Spring, and .NET, FastMCP does not
prescribe a strict architecture. Without widely shared project conventions, **tightly coupled
components, module-level globals, and related anti-patterns are common in Python codebases**, in
part because package docs favor short examples that use global state for brevity. The risk is
sharper in AI-assisted development: each existing pattern becomes the baseline the next
change copies. This template is a starting architecture that follows best practices from the
first commit, so you can spend the remaining effort on the product.

The guiding constraint: nothing important is reachable through a module-level global. No global
config object, no global logger, no import-time singletons. Every component declares what it needs
in its `__init__`, and a **single composition root** (`LifecycleManager`) wires those
dependencies together. That is what makes the code testable without monkeypatching and without
import-order surprises.

This template does not ship a database. For an MCP server, a database is not the usual
resource: a tool is more likely to call a service client than to query a database
itself. Redis is here only so the notes sample has a store.

## Architecture

The application is a three-layer stack. Imports point downward only.

```
                         main.py
                            |
                       lifecycle/          composition root: builds the graph
                            |
   . . . . . . . . . . . . .|. . . . . . . . . . . . . . . . . . . .
                            v
   Protocol surface   http_routes/  mcp_primitives/  middlewares/  prometheus/
                                                custom HTTP routes, MCP primitives,
                                                ASGI middleware, scrape endpoint
                                                siblings: none of the four imports another
   . . . . . . . . . . . . .|. . . . . . . . . . . . . . . . . . . .
                            v
                       state/                  typed AppState + accessors
   . . . . . . . . . . . . .|. . . . . . . . . . . . . . . . . . . .
                            v
   Service layer       services/               business logic
   . . . . . . . . . . . . .|. . . . . . . . . . . . . . . . . . . .
                            v
   Data access layer   clients/                redis, external APIs

   Imports point downward only. A client never imports a service, and never
   imports FastMCP.

   Cross-cutting, importable from any layer, importing none of them:
       models/     config/     logger/     metrics/     distribution/
```

A registrator calls a service; a service calls a client. A Redis client that imports FastMCP is the
canonical violation: it creates a cycle between the HTTP and data access layers.

`lifecycle/` is the one package allowed to import every layer — that is what a composition root is
for. `models/`, `config/`, `logger/`, `metrics/` and `distribution/` sit below everything so they
cannot import back up.

The import graph must stay a DAG. **Python tolerates cycles; this codebase does not**. Adding a new
top-level package fails the contract until it is placed in the hierarchy, so every insertion is
forced to declare where it sits. `uv run lint-imports` enforces both rules from `pyproject.toml`.

### Avoiding hidden cyclic dependencies

A cycle is not a style nit. Python will import `A` while `B` is still half-initialized, so
construction order becomes whoever got imported first instead of a decision the composition root
made. Tests then cannot build one dependency without dragging in the other, which is how suites
**slide into monkeypatching and process-wide setup**. The stack is a DAG so `LifecycleManager` can
start resources in topological order and tear them down in reverse; a cycle turns that into a race
of who exists before whom.

Import Linter only sees **directory-sized** layers: `services/` must not import `http_routes/`. Two
modules in the same package — `orders_service.py` importing `billing_service.py` and back —
still compile, still pass `uv run lint-imports`, and are still a cycle. Same-layer packages listed
with `|` (`http_routes | mcp_primitives | middlewares | prometheus`) are the sibling set the linter does catch. Everything else at one level is the developer's job.

## Layout

| Path | Contents |
| --- | --- |
| `src/app/config/` | Pydantic settings and immutable protocol constants |
| `src/app/lifecycle/` | The composition root: `LifecycleManager`, startup and shutdown |
| `src/app/state/` | Typed `AppState` and the accessors handlers call |
| `src/app/logger/` | `LogManager`, the factory for injectable structured child loggers |
| `src/app/metrics/` | Prometheus collectors injected into services; not HTTP-aware |
| `src/app/distribution/` | Installed dist metadata for the `app` import (`app.version`) |
| `src/app/models/` | Shared Pydantic models used by services and registrators |
| `src/app/clients/` | Data access clients for Redis and external APIs |
| `src/app/services/` | Business services; the layer registrators and middleware depend on |
| `src/app/http_routes/` | Custom HTTP registrators (`register_k8s_probes`) |
| `src/app/mcp_primitives/` | MCP registrators. The shipped example is `register_user_notes_primitives` |
| `src/app/middlewares/` | ASGI middleware wrapping the HTTP surface |
| `src/app/prometheus/` | HTTP instrumentation: scrape endpoint and HTTP-aware series |
| `src/app/main.py` | Process entry point |
| `compose.yaml` | Local Redis only |
| `Dockerfile` | Production image; the default command starts the server |

Each `src/app/` directory has its own README explaining what belongs there.

## Configuration

Configuration is a composition of resource-specific Pydantic models under a single `AppConfig`
(see [src/app/config/README.md](src/app/config/README.md)). Environment variables follow the
nested model path, joined by `__`: `AppConfig.redis.HOST` comes from `REDIS__HOST`.
`.env.example` documents every supported variable.

Validation is strict and fails at startup rather than at first use: ports are range-checked,
passwords are `SecretStr`, and cross-cutting rules (such as forbidding debug logging in production)
are enforced by model validators.

## Logging

Every record is one JSON object, including uvicorn startup lines, so the same keys can be
filtered in grep or in Grafana, Datadog, or Groundcover. There is no process-wide
`structlog.configure()`; [`LogManager`](src/app/logger/README.md) stamps identity on each
record and hands out a named child, which is what makes a test inject a logger instead of
patching a global.

```json
{"context": "uvicorn", "env": "local", "app": "fastmcp-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-09-22T05:30:41.991882Z", "msg": "Started server process [31796]"}
```

That line has no `correlation_id`: it is process startup, not a request. The keys on it:

- `context` — the component (`get_child_logger` name, a route's `name=`, or a bridge such as `uvicorn`)
- `env` — `local` / `dev` / `staging` / `prod`
- `app` — fixed `APP_NAME`, not an env var
- `instance` — hostname of this process
- `app.version` — installed distribution version, injected by the composition root
- `level`, `ts` (UTC, `Z` suffix), `msg`

An HTTP line also carries `correlation_id`, bound by `CorrelationIdMiddleware` so the route,
service, and client share it.

`LogManager` receives a `LoggerConfig` and hands out children through `get_child_logger(name)`.
Components take a logger in `__init__` and never call a global one.

Uncaught `asyncio`, Starlette `Exception`, and `sys.excepthook` paths, plus the
`uvicorn.error`, `uvicorn.access`, and `fastmcp` stdlib loggers, are rewritten onto
those children. `context` values and `LOGGER__ENABLE_UVICORN_ACCESS_LOGS` are documented in
[src/app/logger/README.md](src/app/logger/README.md). A start-to-stop process-lifetime transcript
is under [Running locally](#running-locally).

## Demonstrative Feature - User Notes

`UserNotesService` is the sample, registered as the `user-notes.add_note` tool, the
`user-notes://notes` resource, and the `user-notes.get_prompt` prompt. Those
primitives are registered in
[`src/app/mcp_primitives/register_user_notes_primitives.py`](src/app/mcp_primitives/register_user_notes_primitives.py).
Each feature gets its own `register_<feature>` function. The function takes that
feature's dependencies as arguments, and `LifecycleManager` injects them.

### Logging

A UserNotes call also carries `tenant_id` and `user_id`. `get_user_details` is a `Depends`
factory and an async context manager: FastMCP enters it before the primitive body and
exits it after the body returns, and the body binds those two ids with structlog context
variables. Most primitives do not log. The service logger picks up the same ids because
it runs inside that call. Do not add middleware for `X-Tenant-ID` or `X-User-ID`, and do
not pass those ids on each `info()`.

```json
{"context": "user-notes.add_note", "env": "local", "app": "fastmcp-polyrepo-template", "instance": "api-1", "app.version": "1.0.0", "level": "info", "ts": "2026-10-03T00:00:00.000000Z", "msg": "user_notes.add_note", "correlation_id": "6f1d3c2a-9b4e-4c11-8a2f-0e7b1d4a9c33", "tenant_id": "tenant-a", "user_id": "user-1"}
```

Those two fields are present for the whole primitive call, including the service log. A unit
or integration test that calls `UserNotesService` directly never enters `get_user_details`, so
the ids are absent there.

## Running locally

### Requirements

- Python 3.14 (pinned in `.python-version`; `uv` can install it)
- [uv](https://docs.astral.sh/uv/) for dependency management
- [Docker Desktop](https://docs.docker.com/desktop/) (Compose v2) for local Redis

### Setup

```bash
uv sync
uv run pre-commit install
cp .env.example .env
```

`uv sync` installs the dev tools. `uv run pre-commit install` registers the Git hook once per
clone so commits run the checks in [Pre-commit hooks](#pre-commit-hooks).

`.env.example` is a working local configuration for the Compose stack, not a list of
placeholders. Copy it before `docker compose up` so Compose interpolation and the
app share one file. `.env` is git-ignored.

### Compose and serve

Compose is **local-only**: it runs Redis on loopback. The HTTP process stays on
the host so `.env` can keep `127.0.0.1` instead of Docker DNS names.

From the repository root:

```bash
docker compose up -d --wait
uv run app
```

The MCP endpoint is `POST` [`http://127.0.0.1:8080/mcp`](http://127.0.0.1:8080/mcp)
(`SERVER__MCP_PATH`). Kubernetes probes are unprefixed `GET /livez` and `GET /readyz`.
Prometheus scrapes unprefixed `GET /metrics`. The server is stateless streamable HTTP:
no session id, and one request may stream progress unless
`SERVER__ENABLE_SSE_STREAM_RESPONSE` is false.

<details>
<summary>Example stdout from <code>uv run app</code> (structured JSON, one object per line)</summary>

```
{"context": "LifecycleManager", "env": "local", "app": "fastmcp-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-10-03T09:24:00.000000Z", "msg": "lifecycle.app.creating"}
{"context": "LifecycleManager", "env": "local", "app": "fastmcp-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-10-03T09:24:00.000375Z", "msg": "lifecycle.app_state.building"}
{"context": "LifecycleManager", "env": "local", "app": "fastmcp-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-10-03T09:24:00.003880Z", "msg": "lifecycle.features.registering"}
{"context": "LifecycleManager", "env": "local", "app": "fastmcp-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-10-03T09:24:00.073136Z", "msg": "lifecycle.middlewares.registering"}
{"context": "uvicorn", "env": "local", "app": "fastmcp-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-10-03T09:24:00.271118Z", "msg": "Started server process [20496]"}
{"context": "uvicorn", "env": "local", "app": "fastmcp-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-10-03T09:24:00.271438Z", "msg": "Waiting for application startup."}
{"context": "LifecycleManager", "env": "local", "app": "fastmcp-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-10-03T09:24:00.290013Z", "msg": "lifecycle.resources.initializing"}
{"context": "RedisClient", "env": "local", "app": "fastmcp-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-10-03T09:24:00.290311Z", "msg": "redis.starting"}
{"context": "RedisClient", "env": "local", "app": "fastmcp-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-10-03T09:24:00.296947Z", "msg": "redis.started"}
{"context": "uvicorn", "env": "local", "app": "fastmcp-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-10-03T09:24:00.298540Z", "msg": "Application startup complete."}
{"context": "uvicorn", "env": "local", "app": "fastmcp-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-10-03T09:24:00.299524Z", "msg": "Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)"}
{"context": "uvicorn", "env": "local", "app": "fastmcp-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-10-03T09:24:43.500831Z", "msg": "Shutting down"}
{"context": "uvicorn", "env": "local", "app": "fastmcp-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-10-03T09:24:43.609072Z", "msg": "Waiting for application shutdown."}
{"context": "LifecycleManager", "env": "local", "app": "fastmcp-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-10-03T09:24:43.610610Z", "msg": "lifecycle.resources.tearing_down"}
{"context": "RedisClient", "env": "local", "app": "fastmcp-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-10-03T09:24:43.611250Z", "msg": "redis.stopping"}
{"context": "RedisClient", "env": "local", "app": "fastmcp-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-10-03T09:24:43.612774Z", "msg": "redis.stopped"}
{"context": "uvicorn", "env": "local", "app": "fastmcp-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-10-03T09:24:43.613958Z", "msg": "Application shutdown complete."}
{"context": "uvicorn", "env": "local", "app": "fastmcp-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-10-03T09:24:43.614787Z", "msg": "Finished server process [20496]"}
```

</details>

Stop the dependency stack with `docker compose down`.

Hosts in `.env` are `127.0.0.1`, not `localhost`, so Windows does not stall on IPv6 while Docker
Desktop publishes IPv4 only. Inside a container network, point `REDIS__HOST` at the service
name `redis`.

### One process per container

Uvicorn can take a live ASGI app (what `main.py` passes) or an import string such as
`app.main:app`. The string exists so a **new** process can import a fresh app; you cannot hand
a live in-memory graph to a child. `--reload` (restart on file change) and `--workers N`
(N processes behind one master) both need that string. `--reload` is a laptop convenience
and stays out of the entry point.

`--workers` is the classic one-VM pattern (Gunicorn-style workers on a single box). This
README's production shape is Kubernetes: **one app process per container, N Pods for
throughput**. Liveness and readiness probes, `SIGTERM`, memory limits, and HPA all assume
that. The same parallelism is **several small Pods** (about 1–2 cores each). The scheduler,
rolling deploys, and "this replica is sick" then match one process. Eight workers inside one
container look like **one** container to the kubelet: CPU and memory requests become a guess,
and a kill of the container kills every worker.

## Container image

The [Dockerfile](Dockerfile) is a production-style image (multi-stage, non-root, frozen lockfile,
no `.env`). The virtualenv is owned by root; the runtime user cannot rewrite it. It is **not**
used by the default local loop.

```bash
docker build -t fastmcp-polyrepo-template .
```

The default command starts the server:

```bash
docker run --rm -p 8080:8080 --env-file .env fastmcp-polyrepo-template
```

## Production deploy

This repository does not ship Helm or Kubernetes YAML.

## Testing

```bash
uv run pytest
```

Three trees, one invocation. Layout under each tree mirrors `src/app/`. Docker Desktop must be running for integration and e2e;
`uv run pytest tests/unit` does not start containers.

```bash
uv run pytest tests/unit
uv run pytest tests/integration
uv run pytest tests/e2e
```

- **Unit** ([tests/unit/](tests/unit/README.md)): In-process. Redis is an injected double
  (`AsyncMock`), so nothing binds a socket.
- **Integration** ([tests/integration/](tests/integration/README.md)): A service against
  throwaway Redis via Testcontainers. The directory, README, and `redis_client` fixture
  are in place; test modules arrive with the next Redis-backed use case.
- **End-to-end** ([tests/e2e/](tests/e2e/README.md)): HTTP through `LifecycleManager` against
  the same throwaway Redis. Probe tests are the coverage that ships today.

## Linting and type checking

```bash
uv run ruff format .
uv run ruff check .
uv run pyright
uv run lint-imports
```

[Ruff](https://docs.astral.sh/ruff/) both formats and lints: 100-column lines, double quotes, and a
broad rule set that includes Google-style docstring checks, import sorting, and a ban on `print`.
Formatting is the formatter's job alone — the quote and comma lint rules are deliberately left off
because they fight it.

[Pyright](https://microsoft.github.io/pyright/) runs in strict mode over `src` and `tests`.

[Import Linter](https://import-linter.readthedocs.io/) enforces the one-directional stack: an
upward import, a cycle, or a new top-level package that has not been placed in the hierarchy all
fail the contract. So does a service or client that imports FastMCP or Starlette.

All three are configured in `pyproject.toml`, and every rule exemption there carries a comment
explaining itself.

## Pre-commit hooks

The same four commands, plus `uv audit --locked --preview-features audit-command`, run on
`git commit` via [pre-commit](https://pre-commit.com/). Format in the hook is
`ruff format --check .`, so an unformatted tree fails the commit instead of rewriting it.
The audit hook needs a network to fetch advisories. A CVE published while `main` is idle
is still caught by the weekly Audit workflow, because the lock does not change when the
advisory appears.

After `uv sync`, install the hook once:

```bash
uv run pre-commit install
```

## CI

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on pushes and pull requests to `main`:
ruff, pyright, import-linter, the full pytest suite (unit, integration, and e2e — GitHub-hosted
Ubuntu has Docker, so Testcontainers can start), and `docker build` with no push. There is no
deploy workflow: where an image goes is a product decision, not a template one.

[`.github/workflows/audit.yml`](.github/workflows/audit.yml) runs `uv audit --locked` on those
same events and weekly, so a CVE published while `main` is idle still fails the Audit badge.
Dependabot ([`.github/dependabot.yml`](.github/dependabot.yml)) opens weekly PRs for the `uv`
lockfile and for GitHub Actions; outdated packages without a known CVE do not fail Audit.

## Authentication

This template does not ship authentication. The scheme is a product choice (bearer
token, mTLS, or none). Many deployments never authenticate in-process: an API
gateway or mesh already did. Shipping one scheme would become the pattern every
later change — including AI-assisted ones — copies.

`X-Tenant-ID` and `X-User-ID` name the caller for logs and Redis keys. They are
not authentication.
