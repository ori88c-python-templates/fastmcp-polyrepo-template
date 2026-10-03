# tests

The test suite, split by how much of the real world a test is allowed to touch.

| Path | What belongs there |
| --- | --- |
| [`unit/`](unit/README.md) | In-process tests. Dependencies are injected (buffers, temp files, `AsyncMock`). |
| [`integration/`](integration/README.md) | A service against real Redis via Testcontainers. `services/user_notes_service/` is the example. |
| [`e2e/`](e2e/README.md) | The real application against Testcontainers. Probes use the HTTP `client`. MCP primitives use `open_mcp_client`. |

Within each tree, layout mirrors `src/app/`: one directory per package, then one
directory per component under test, then one file per feature.

## Running

```bash
uv run pytest
uv run pytest -v
uv run pytest tests/unit
uv run pytest tests/integration
uv run pytest tests/e2e
```

`testpaths` in `pyproject.toml` lists `tests/unit`, then `tests/integration`, then `tests/e2e`, so a bare `uv run pytest` collects in that order. Integration and e2e
need Docker Desktop; those tests skip if the daemon is down. `uv run pytest tests/unit` never starts
a container.

Conventions are defined in [.cursor/rules/tests.mdc](../.cursor/rules/tests.mdc).
