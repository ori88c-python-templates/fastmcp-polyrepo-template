"""Immutable protocol constants that must not be overridden by the environment.

Header names, the request-state correlation id key, unprefixed infrastructure
paths, the log ``app`` identity, and the MCP server name and instructions are a
contract with callers (kubelet, Prometheus, inbound tracing, observability, MCP
clients). They are not deployment settings: putting them in ``.env`` would invite
a typo to break every probe, scrape, Grafana filter, or ``server/discover`` name.
"""

from typing import Final

APP_NAME: Final = "fastmcp-polyrepo-template"
MCP_SERVER_NAME: Final = "FastMCP Polyrepo Template"
MCP_SERVER_INSTRUCTIONS: Final = "Redis-backed process with probes and Prometheus."
REQUEST_ID_HEADER: Final = "X-Request-ID"
TENANT_ID_HEADER: Final = "X-Tenant-ID"
USER_ID_HEADER: Final = "X-User-ID"
CORRELATION_ID_HEADER: Final = "X-Correlation-ID"
CORRELATION_ID_STATE_KEY: Final = "correlation_id"
METRICS_ENDPOINT: Final = "/metrics"
LIVEZ_ENDPOINT: Final = "/livez"
READYZ_ENDPOINT: Final = "/readyz"
