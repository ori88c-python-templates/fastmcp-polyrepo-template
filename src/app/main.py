"""Process entry point."""

import uvicorn

from app.config import AppConfig
from app.lifecycle import LifecycleManager


def main() -> None:
    """Load configuration, install process hooks, build the app, and serve it.

    Configuration is read first and separately so that an invalid environment fails
    here, before a single resource is constructed. The sys.excepthook and uvicorn
    bridges are process-wide, so they are installed here rather than inside
    ``create_app``. ``log_config=None`` keeps uvicorn from wiping those handlers
    with its default ``dictConfig``. ``access_log`` follows
    ``LOGGER__ENABLE_UVICORN_ACCESS_LOGS`` so uvicorn does not clear a handler we
    just attached, and so a disabled flag emits no access lines at all.
    """
    # AppConfig reads every field from the environment, but `redis` has no
    # default, so the type checker sees an incomplete call it has no way to know
    # is satisfied at runtime.
    app_config = AppConfig()  # pyright: ignore[reportCallIssue]
    lifecycle = LifecycleManager(app_config)
    lifecycle.install_process_logging()
    app = lifecycle.create_app()

    uvicorn.run(
        app,
        host=app_config.server.HOST,
        port=app_config.server.PORT,
        log_config=None,
        access_log=app_config.logger.ENABLE_UVICORN_ACCESS_LOGS,
    )


if __name__ == "__main__":
    main()
