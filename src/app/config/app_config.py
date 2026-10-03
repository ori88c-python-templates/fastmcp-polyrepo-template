"""The application's root configuration model."""

from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config.logger_config import LoggerConfig, LogLevel
from app.config.prometheus_config import PrometheusConfig
from app.config.redis_config import RedisConfig
from app.config.server_config import ServerConfig


class Environment(StrEnum):
    """The deployment environment the process is running in.

    ``LOCAL`` is a developer machine, as distinct from ``DEV``, which is a shared
    deployed environment.
    """

    LOCAL = "local"
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"

    def include_probes_in_schema(self) -> bool:
        """Whether Kubernetes probe routes set Starlette's ``include_in_schema``.

        This process does not serve ``/docs`` or an OpenAPI document. The flag is
        the route bit a schema generator would read. Local and shared-dev set it
        so a later generator can list the probes. Staging and production leave it
        unset: kubelet is the only caller, and the paths are not product API.
        MCP clients learn tools from ``server/discover``, which does not list them.

        Returns:
            True when this environment is ``local`` or ``dev``.
        """
        return self in (Environment.LOCAL, Environment.DEV)


class AppConfig(BaseSettings):
    """Root configuration, composed of one model per resource.

    Values are read from the process environment and from ``.env``. Names follow the
    nested model path, joined by ``__``: ``AppConfig.redis.HOST`` comes from
    ``REDIS__HOST``. Matching is case-insensitive, so environment variables are
    written in upper case by convention.

    ``redis`` has no default: a deployment that fails to supply it fails at startup
    rather than at first use.

    Attributes:
        ENV: The deployment environment.
        server: Bind address and the stateless MCP HTTP endpoint.
        logger: Structured logging settings.
        redis: Redis connection settings.
        prometheus: Scrape-endpoint settings. Optional in the environment;
            gzip defaults to off.
    """

    model_config = SettingsConfigDict(
        env_prefix="",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    ENV: Environment = Environment.DEV
    server: ServerConfig = Field(default_factory=ServerConfig)
    logger: LoggerConfig = Field(default_factory=LoggerConfig)
    redis: RedisConfig
    prometheus: PrometheusConfig = Field(default_factory=PrometheusConfig)

    @model_validator(mode="after")
    def _enforce_production_invariants(self) -> Self:
        """Reject configurations that are individually valid but wrong for production.

        Each resource model can only validate itself. Rules that span models, such as
        "debug logging is never acceptable in production", have to live here.

        Returns:
            The validated model.

        Raises:
            ValueError: If ``ENV`` is ``prod`` and a setting is unsafe for production.
        """
        if self.ENV is not Environment.PROD:
            return self

        if self.logger.MIN_LOG_LEVEL is LogLevel.DEBUG:
            raise ValueError(
                "LOGGER__MIN_LOG_LEVEL=debug is not allowed when ENV=prod: "
                "debug logging risks writing sensitive payloads to the log stream."
            )

        return self
