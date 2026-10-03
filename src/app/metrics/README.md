# metrics

Prometheus collectors that **services and clients** increment.

This package talks to [`prometheus_client`](https://github.com/prometheus/client_python)
only. It must not import FastMCP, FastAPI, or Starlette. Business series for a
use case are added here and re-exported from [`__init__.py`](__init__.py).
[`user_notes_metrics.py`](user_notes_metrics.py) counts note reads and writes.

It is not [`prometheus/`](../prometheus/README.md). That sibling of `http_routes/`,
`mcp_primitives/`, and `middlewares/` owns the scrape endpoint and HTTP-aware series. This package owns
collectors injected into services.

## Table of Contents

- [Two kinds of custom metric](#two-kinds-of-custom-metric)
- [Dependency injection](#dependency-injection)

## Two kinds of custom metric

- **HTTP-aware** (request headers, status, path): defined in
  [`prometheus/`](../prometheus/README.md). The dummy series
  `http_requests_with_inbound_request_id_total` is the example.
- **Business** (a use case happened): defined here and injected into the service.
  Add the collector class in the same change as the service that increments it.

Default request latency and count come from
`prometheus_fastapi_instrumentator` and are wired in `LifecycleManager`, not here.

## Dependency injection

A collector is constructed once, on the same `CollectorRegistry` the `/metrics`
endpoint scrapes, and passed into the component that increments it. Components do
not call `Counter(...)` themselves: that would register a process-wide global.
The composition root always passes `PrometheusManager.registry`; there is no
default to the process-wide `REGISTRY`.
