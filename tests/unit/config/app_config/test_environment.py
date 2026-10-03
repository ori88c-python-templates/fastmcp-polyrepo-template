"""Deployment environment schema-flag policy."""

import pytest

from app.config import Environment


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        (Environment.LOCAL, True),
        (Environment.DEV, True),
        (Environment.STAGING, False),
        (Environment.PROD, False),
    ],
)
def test_include_probes_in_schema_is_local_and_dev_only(
    env: Environment,
    expected: bool,
) -> None:
    """Kubelet probes are marked for a schema generator only in local and dev."""
    assert env.include_probes_in_schema() is expected
