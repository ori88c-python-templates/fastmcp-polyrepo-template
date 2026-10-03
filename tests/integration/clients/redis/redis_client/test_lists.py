"""List append and read against real Redis."""

from typing import Final

from app.clients import RedisClient

_KEY: Final = "lists:alpha"
_OTHER_KEY: Final = "lists:beta"


async def test_two_appends_are_read_oldest_first(redis_client: RedisClient) -> None:
    """Items come back in the order they were appended."""
    await redis_client.append_list_item(_KEY, "first")
    await redis_client.append_list_item(_KEY, "second")

    assert await redis_client.read_list(_KEY) == ["first", "second"]


async def test_a_second_key_does_not_see_the_items(redis_client: RedisClient) -> None:
    """Each key is its own list."""
    await redis_client.append_list_item(_KEY, "only-here")

    assert await redis_client.read_list(_OTHER_KEY) == []


async def test_read_list_on_a_missing_key_returns_nothing(redis_client: RedisClient) -> None:
    """A key that was never written is an empty list, not an error."""
    assert await redis_client.read_list(_KEY) == []
