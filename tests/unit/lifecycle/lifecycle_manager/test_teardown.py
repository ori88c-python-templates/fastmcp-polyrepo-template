"""A failed close is logged and does not skip the remaining resources."""

import asyncio
from io import BytesIO
from typing import cast
from unittest.mock import AsyncMock

from app.clients import RedisClient
from app.config import AppConfig, Environment, RedisConfig
from app.lifecycle import LifecycleManager
from app.state import AppState
from tests.unit.app_state_factory import AppStateFactory
from tests.unit.logger.log_manager.helpers import read_records

_TASK_NAME = "event-loop-lag"
_STOP_FAILED = "lifecycle.resource.stop_failed"


async def test_failed_redis_stop_is_logged_and_the_probe_still_stops(
    sink: BytesIO,
    make_app_state: AppStateFactory,
) -> None:
    """Redis ``stop`` raising does not leave the lag probe running.

    The failure is a ``lifecycle.resource.stop_failed`` record on the manager's
    stream, and teardown itself does not raise.
    """
    redis = AsyncMock(spec=RedisClient)
    redis.stop.side_effect = RuntimeError("boom")
    state: AppState = make_app_state(redis=cast(RedisClient, redis))
    lifecycle = LifecycleManager(
        AppConfig(ENV=Environment.DEV, redis=RedisConfig(HOST="127.0.0.1")),
        stream=sink,
    )
    lifecycle._event_loop_lag.start()  # pyright: ignore[reportPrivateUsage]

    await lifecycle._teardown_by_reverse_topological_order(state)  # pyright: ignore[reportPrivateUsage]

    running = {task.get_name() for task in asyncio.all_tasks()}
    assert _TASK_NAME not in running
    failed = [record for record in read_records(sink) if record["msg"] == _STOP_FAILED]
    assert len(failed) == 1
    assert failed[0]["resource"] == "redis"
    assert "RuntimeError: boom" in failed[0]["exception"]
