"""Configuration for the Prometheus scrape endpoint."""

from pydantic import BaseModel


class PrometheusConfig(BaseModel):
    """Settings for ``GET /metrics``.

    The scrape path itself is not here: ``/metrics`` is a contract, like
    ``/livez``, and lives in ``app_consts``. Schema inclusion is not here
    either: the scrape path is never marked ``include_in_schema``.

    Attributes:
        SHOULD_GZIP: Whether to gzip when the client sends ``Accept-Encoding``.
            Defaults to ``False``: the library prefers CPU over extra bandwidth.
    """

    SHOULD_GZIP: bool = False
