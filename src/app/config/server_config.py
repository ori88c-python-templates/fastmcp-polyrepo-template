"""Configuration for the stateless MCP HTTP server."""

from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

from app.config.app_consts import LIVEZ_ENDPOINT, METRICS_ENDPOINT, READYZ_ENDPOINT


class ServerConfig(BaseModel):
    """Bind address and the streamable HTTP endpoint operators change.

    The process always serves streamable HTTP in stateless mode. There is no
    session store and no legacy SSE transport. Those are fixed in the
    composition root, not toggles here: turning them off would put protocol
    sessions back.

    Attributes:
        HOST: Interface to bind to. Defaults to ``0.0.0.0`` so the process is
            reachable from outside its container.
        PORT: TCP port to listen on. Constrained to the valid port range.
        MCP_PATH: Path of the streamable HTTP endpoint. Defaults to ``/mcp``.
        ENABLE_SSE_STREAM_RESPONSE: When true, one stateless request may stream
            progress as server-sent events. When false, that request returns a
            single JSON body. Defaults to true so a tool can report progress.
    """

    # S104: binding to all interfaces is required, not accidental. A container's service has to
    # be reachable from outside its network namespace; exposure is controlled at the network layer.
    HOST: str = Field(default="0.0.0.0", min_length=1)  # noqa: S104
    PORT: int = Field(default=8080, ge=1, le=65535)
    MCP_PATH: str = Field(default="/mcp", min_length=1)
    ENABLE_SSE_STREAM_RESPONSE: bool = True

    @field_validator("MCP_PATH")
    @classmethod
    def _mcp_path_is_absolute(cls, value: str) -> str:
        """Require a URL path, not a host or a query string.

        Args:
            value: The configured MCP endpoint path.

        Returns:
            The same path when it is absolute and has no query or fragment.

        Raises:
            ValueError: If the path is not a single absolute URL path.
        """
        if not value.startswith("/") or "?" in value or "#" in value:
            raise ValueError("MCP_PATH must be an absolute path without a query or fragment.")
        return value

    @model_validator(mode="after")
    def _mcp_path_is_not_an_infrastructure_route(self) -> Self:
        """Keep the MCP endpoint off the probe and scrape paths.

        Returns:
            This config when ``MCP_PATH`` does not collide with kubelet or
            Prometheus.

        Raises:
            ValueError: If ``MCP_PATH`` is ``/livez``, ``/readyz``, or ``/metrics``.
        """
        if self.MCP_PATH in {LIVEZ_ENDPOINT, READYZ_ENDPOINT, METRICS_ENDPOINT}:
            raise ValueError("MCP_PATH must not reuse a probe or metrics path.")
        return self
