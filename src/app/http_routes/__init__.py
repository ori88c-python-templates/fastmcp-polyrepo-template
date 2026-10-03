"""HTTP registration on the FastMCP server."""

from app.http_routes.get_http_route_logger import get_http_route_logger
from app.http_routes.register_k8s_probes import register_k8s_probes

__all__ = ["get_http_route_logger", "register_k8s_probes"]
