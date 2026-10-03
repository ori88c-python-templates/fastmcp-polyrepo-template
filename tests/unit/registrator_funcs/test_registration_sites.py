"""Registration calls are legal only inside the matching registrator package."""

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_APP_ROOT = _REPO_ROOT / "src" / "app"

# Longer names come first so `.add_tool(` is not also read as `.tool(`.
_MCP_METHODS = (
    "add_completion_handler|add_template|add_resource|add_prompt|add_tool"
    "|tool|resource|prompt|completion"
)
_HTTP_REGISTRATION = re.compile(r"\.custom_route\s*\(|@\w+\.custom_route\b")
_MCP_REGISTRATION = re.compile(rf"\.(?:{_MCP_METHODS})\s*\(|@\w+\.(?:{_MCP_METHODS})\b")


def _is_registrator(path: Path, package: str) -> bool:
    """Return whether ``path`` is ``src/app/<package>/register_*.py``.

    Args:
        path: A Python file under ``src/app``.
        package: ``http_routes`` or ``mcp_primitives``.

    Returns:
        True when the file is a registrator module directly in that package.
    """
    return (
        path.parent.name == package
        and path.parent.parent.name == "app"
        and path.name.startswith("register_")
        and path.suffix == ".py"
    )


def test_registration_calls_stay_in_registrators() -> None:
    """Fail with file and line when a registration call sits outside its package.

    ``custom_route`` belongs in ``src/app/http_routes/register_*.py``. MCP
    registration methods belong in ``src/app/mcp_primitives/register_*.py``.
    When FastMCP adds a registration method, add its name to ``_MCP_METHODS``
    in the same change.
    """
    violations: list[str] = []
    for path in sorted(_APP_ROOT.rglob("*.py")):
        http_home = _is_registrator(path, "http_routes")
        mcp_home = _is_registrator(path, "mcp_primitives")
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            relative = path.relative_to(_REPO_ROOT).as_posix()
            if _HTTP_REGISTRATION.search(line) and not http_home:
                violations.append(
                    f"{relative}:{line_number}: custom_route outside http_routes/register_*.py"
                )
            if _MCP_REGISTRATION.search(line) and not mcp_home:
                violations.append(
                    f"{relative}:{line_number}: MCP registration outside mcp_primitives registrator"
                )

    assert not violations, "\n".join(violations)
