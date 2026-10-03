"""A colon inside a part does not merge that part with the next one."""

from app.clients import create_redis_key


def test_length_prefixes_keep_colon_split_callers_apart() -> None:
    """Tenant ``a`` / user ``b:c`` is a different key from tenant ``a:b`` / user ``c``."""
    first = create_redis_key("user_notes", "a", "b:c")
    second = create_redis_key("user_notes", "a:b", "c")

    assert first == "user_notes:1:a:3:b:c"
    assert second == "user_notes:3:a:b:1:c"
    assert first != second
