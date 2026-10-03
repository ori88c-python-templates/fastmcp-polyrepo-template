"""Construction, startup and shutdown of the FastMCP HTTP application."""

import asyncio
import sys
from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Final

from fastmcp import FastMCP
from starlette.applications import Starlette

from app.clients import RedisClient
from app.config import MCP_SERVER_INSTRUCTIONS, MCP_SERVER_NAME, AppConfig
from app.distribution import installed_app_version
from app.http_routes import register_k8s_probes
from app.logger import (
    LogManager,
    install_fastmcp_logging,
    install_uvicorn_access_logging,
    install_uvicorn_error_logging,
    make_asyncio_exception_handler,
    make_sys_excepthook,
)
from app.mcp_primitives import UserNotesMcpLoggers, register_user_notes_primitives
from app.metrics import UserNotesMetrics
from app.middlewares import (
    CorrelationIdMiddleware,
    make_unhandled_http_exception_handler,
)
from app.prometheus import (
    PrometheusManager,
    make_inbound_request_id_instrumentation,
)
from app.services import UserNotesService
from app.state import (
    APP_STATE_ATTRIBUTE,
    AppClients,
    AppServices,
    AppState,
)

_LIFECYCLE_LOGGER_NAME: Final = "LifecycleManager"
_REDIS_LOGGER_NAME: Final = "RedisClient"
_UVICORN_LOGGER_NAME: Final = "uvicorn"
_UVICORN_ACCESS_LOGGER_NAME: Final = "uvicorn.access"
_ASYNCIO_LOGGER_NAME: Final = "asyncio"
_SYS_EXCEPTHOOK_LOGGER_NAME: Final = "sys.excepthook"
_FASTMCP_LOGGER_NAME: Final = "fastmcp"
_USER_NOTES_LOGGER_NAME: Final = "UserNotesService"
_USER_NOTES_ADD_NOTE_LOGGER_NAME: Final = "user-notes.add_note"


class LifecycleManager:
    """Builds the application and owns the order its resources start and stop in.

    This is the composition root: the one place that constructs dependencies and hands
    them to each other. Nothing else in the codebase calls a constructor for a client,
    a service or a logger, which is what keeps the rest of the app free of global state.

    A class rather than a set of functions because every step wants the same two things,
    the configuration and a logger, and threading both through six function signatures
    is noise. Built once, in ``main``.
    """

    def __init__(self, app_config: AppConfig) -> None:
        """Prepare the manager and the logging every later step reports through.

        The ``LogManager`` is built here rather than during ``create_app`` because it is
        the one dependency the manager itself needs: it has to be able to log the
        construction of everything else, including the failures.

        Args:
            app_config: Fully validated configuration, built by the caller so that a bad
                environment fails before anything is constructed.
        """
        self._app_config: Final = app_config
        self._app_version: Final = installed_app_version()
        self._log_manager: Final = LogManager(
            app_config.logger,
            env=app_config.ENV,
            app_version=self._app_version,
        )
        self._logger: Final = self._log_manager.get_child_logger(_LIFECYCLE_LOGGER_NAME)
        self._prometheus: Final = PrometheusManager()
        self._prometheus.add_http_instrumentation(
            make_inbound_request_id_instrumentation(self._prometheus.registry),
        )

    def create_app(self) -> Starlette:
        """Build the application and everything it depends on.

        The state is attached before the application is returned, so it is in place well
        before the server runs the lifespan and long before the first request.

        Returns:
            The Starlette app from ``FastMCP.http_app``, ready to be served.
        """
        self._logger.info("lifecycle.app.creating", env=self._app_config.ENV.value)

        app_state = self._build_app_state()
        mcp = FastMCP(
            MCP_SERVER_NAME,
            version=self._app_version,
            instructions=MCP_SERVER_INSTRUCTIONS,
            lifespan=self._make_lifespan(app_state),
            mask_error_details=True,
        )
        self._logger.info("lifecycle.features.registering")
        register_k8s_probes(
            mcp,
            include_in_schema=self._app_config.ENV.include_probes_in_schema(),
        )
        register_user_notes_primitives(
            mcp,
            app_state.services.user_notes,
            UserNotesMcpLoggers(
                add_note=self._log_manager.get_child_logger(_USER_NOTES_ADD_NOTE_LOGGER_NAME),
            ),
        )
        app = mcp.http_app(
            path=self._app_config.server.MCP_PATH,
            transport="http",
            stateless_http=True,
            json_response=not self._app_config.server.ENABLE_SSE_STREAM_RESPONSE,
            # Not a weaker production setting. Ingress or the reverse proxy already
            # owns the Host header. Turning this guard on without an allowlist
            # returns 421 to kubelet and Prometheus, which do not send a public
            # MCP hostname.
            host_origin_protection=False,
        )
        setattr(app.state, APP_STATE_ATTRIBUTE, app_state)

        app.add_exception_handler(
            Exception,
            make_unhandled_http_exception_handler(
                self._log_manager.get_child_logger(_UVICORN_LOGGER_NAME),
            ),
        )
        self._add_middlewares_in_order(app)
        self._prometheus.add_metrics_router(app, self._app_config.prometheus)

        return app

    def install_process_logging(self) -> None:
        """Install process-wide logging before the server starts.

        ``sys.excepthook`` and the uvicorn error and access bridges are
        process-wide, so ``main`` calls this rather than ``create_app``. Tests
        that only build an app must not replace the process hook. The asyncio
        handler is separate: it needs a running loop and is installed for the
        lifespan.

        ``sys.excepthook`` uses a child named ``sys.excepthook``.
        ``KeyboardInterrupt`` and ``SystemExit`` stay on the interpreter default.

        ``uvicorn.error`` is bridged onto the same ``uvicorn`` child the HTTP 500
        hook uses, including the ASGI exception filter.

        ``fastmcp`` is bridged onto a child named ``fastmcp``. Importing FastMCP
        already attached Rich handlers; this replaces them so an unexpected
        tool, resource, or prompt failure is structured JSON. The client still
        receives FastMCP's masked message, not the exception text.

        ``uvicorn.access`` is bridged only when ``ENABLE_UVICORN_ACCESS_LOGS`` is
        true. ``main`` still passes that flag as ``access_log`` so a disabled
        flag does not leave an empty logger printing via lastResort.
        """
        sys.excepthook = make_sys_excepthook(
            self._log_manager.get_child_logger(_SYS_EXCEPTHOOK_LOGGER_NAME),
        )
        install_uvicorn_error_logging(
            self._log_manager.get_child_logger(_UVICORN_LOGGER_NAME),
        )
        install_fastmcp_logging(
            self._log_manager.get_child_logger(_FASTMCP_LOGGER_NAME),
        )
        if self._app_config.logger.ENABLE_UVICORN_ACCESS_LOGS:
            install_uvicorn_access_logging(
                self._log_manager.get_child_logger(_UVICORN_ACCESS_LOGGER_NAME),
            )

    def _build_app_state(self) -> AppState:
        """Construct every long-lived object, in dependency order.

        The ``LogManager`` is already built. Clients are constructed here but not
        connected: there is no event loop yet. Services are constructed here, after
        their clients.

        Returns:
            The assembled state, with clients unopened until topological init.
        """
        self._logger.info("lifecycle.app_state.building")

        redis_client = RedisClient(
            self._app_config.redis,
            self._log_manager.get_child_logger(_REDIS_LOGGER_NAME),
        )

        return AppState(
            clients=AppClients(redis=redis_client),
            services=AppServices(
                user_notes=UserNotesService(
                    redis_client,
                    self._log_manager.get_child_logger(_USER_NOTES_LOGGER_NAME),
                    UserNotesMetrics(registry=self._prometheus.registry),
                ),
            ),
            log_manager=self._log_manager,
        )

    def _make_lifespan(
        self,
        app_state: AppState,
    ) -> Callable[[FastMCP], AbstractAsyncContextManager[dict[str, object]]]:
        """Build the FastMCP lifespan that starts and stops Redis.

        FastMCP's HTTP lifespan receives the server, not the Starlette app, so
        the state built in ``create_app`` is closed over. ``http_app`` enters
        this through ``_lifespan_manager``. Do not also set a Starlette lifespan:
        that would run startup twice.

        Args:
            app_state: Clients and loggers constructed before the server exists.

        Returns:
            A lifespan callable for ``FastMCP``.
        """

        @asynccontextmanager
        async def lifespan(_server: FastMCP) -> AsyncGenerator[dict[str, object]]:
            """Run resource startup before serving and teardown after.

            Installs the asyncio unhandled-exception hook on the running loop for
            the lifetime of this context, and restores the previous handler after
            teardown so ``stop()`` failures still get structured ``asyncio`` logs.

            Args:
                _server: The FastMCP server entering its lifespan. Unused: Redis
                    lives on the closed-over application state.

            Yields:
                An empty lifespan context. ``LifecycleManager`` is the only
                composition root, so this dict is discouraged: putting Redis or a
                service in it would copy the typed ``AppState`` into an untyped
                bag. Request handlers read ``AppState`` from the Starlette app.
            """
            loop = asyncio.get_running_loop()
            previous_handler = loop.get_exception_handler()
            loop.set_exception_handler(
                make_asyncio_exception_handler(
                    self._log_manager.get_child_logger(_ASYNCIO_LOGGER_NAME),
                )
            )
            try:
                await self._init_by_topological_order(app_state)
                try:
                    # Empty on purpose. LifecycleManager is the only composition
                    # root, so a non-empty dict would duplicate typed AppState.
                    yield {}
                finally:
                    # A crash while serving still has to release connections, so teardown
                    # belongs in `finally` rather than merely after the yield.
                    await self._teardown_by_reverse_topological_order(app_state)
            finally:
                loop.set_exception_handler(previous_handler)

        return lifespan

    async def _init_by_topological_order(self, app_state: AppState) -> None:
        """Open every resource that needs an event loop, dependencies first.

        Connection pools cannot be opened in ``_build_app_state`` because there is no
        running event loop yet, so construction and connection are deliberately separate
        steps. Redis is the only client, and it is started to match the field
        order on ``AppClients``.

        Args:
            app_state: The state whose clients are being started.
        """
        self._logger.info("lifecycle.resources.initializing")

        await app_state.clients.redis.start()

    async def _teardown_by_reverse_topological_order(self, app_state: AppState) -> None:
        """Release every resource, in the exact reverse of the startup order.

        Reverse order is what makes shutdown graceful: a resource is only closed once
        everything that might still call it is already gone.

        The log manager is flushed last for the same reason. It is what everything else
        logs through, so draining it earlier would discard the records written while the
        remaining resources shut down.

        Args:
            app_state: The state being torn down.
        """
        self._logger.info("lifecycle.resources.tearing_down")

        try:
            await app_state.clients.redis.stop()
        finally:
            app_state.log_manager.flush()

    def _add_middlewares_in_order(self, app: Starlette) -> None:
        """Register middleware, outermost last.

        Starlette wraps middleware in reverse registration order, so the last
        ``add_middleware`` call is the outermost: it sees the request first and the
        response last. Registration in this method is therefore:

        1. ``PrometheusManager.add_middleware(app)`` — Prometheus, innermost of
           these two. It measures the application. Header middleware is not a
           useful slice of latency, and keeping it inside correlation id means
           ``/metrics`` still receives ``X-Request-ID``.
        2. ``CorrelationIdMiddleware`` — outermost, so every inner log line picks
           up ``correlation_id`` and every response carries ``X-Request-ID``.

        FastMCP's own ``RequestContextMiddleware`` is already on the app from
        ``http_app`` and stays closer to the application than these two.
        ``add_metrics_router`` is not called here: it mounts a route, not
        middleware.

        Third-party ``instrument(app)`` / ``setup(app)`` helpers often call
        ``app.add_middleware`` themselves. They belong in this method, in the
        intended slot, not after ``create_app()`` returns. Wrapping the app object
        in ``main`` (``app = SomeASGIWrapper(app)``) sits outside this stack.

        Args:
            app: The application to register middleware on.
        """
        self._logger.info("lifecycle.middlewares.registering")

        self._prometheus.add_middleware(app)
        app.add_middleware(CorrelationIdMiddleware)
