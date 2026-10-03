# mcp_primitives

Registration of MCP primitives. A registrator here is `register_<feature>.py`, the
only place a feature may declare an MCP method. Custom HTTP routes live in
[`http_routes/`](../http_routes/README.md), not here. The two packages do not
import each other. See `.cursor/rules/registrator-funcs.mdc`.

[`register_user_notes_primitives.py`](register_user_notes_primitives.py) is the
shipped example. `LifecycleManager.create_app` calls it, with the service and
`UserNotesMcpLoggers`, before `http_app()`. Caller identity is
[`get_user_details`](get_user_details.py) via `Depends(get_user_details)`. Do not
add middleware for `X-Tenant-ID` or `X-User-ID`. A primitive logger is a field on
that feature's frozen dataclass, not a `Depends` parameter.

Client-facing catalog copy is a decorator argument, not the docstring. Pass
`description=` on a tool, resource, and prompt. Omitting it publishes the
docstring. Also pass `title`. A tool that writes passes `annotations`. A
resource whose body is JSON passes `mime_type`. The docstring stays for
developers. See `.cursor/rules/swagger.mdc`.

This directory is the whole MCP surface, not a tools folder. The spec also includes:

- **Registered on the server** in FastMCP 4.0.10: tools, resources (including
  templates), prompts, and completions (`tool` / `add_tool`, `resource` /
  `add_resource` / `add_template`, `prompt` / `add_prompt`, `completion` /
  `add_completion_handler`).
- **Called from inside a registered handler** via `Context`, not as their own
  decorator: elicitation (`elicit`), sampling, client logging (`log`), and
  progress (`report_progress`).
- **Spec or extension surfaces** that still belong in this directory when a
  feature implements them: roots, subscriptions, and tasks (`tasks/get`,
  `tasks/update`, `tasks/cancel`). When FastMCP adds a registration method for
  one of these, the call goes in `register_<feature>.py` here, and the
  registration-site test gains that name in the same change.

A handler calls a service on `AppServices`. It does not construct a client or
copy the readiness probe's direct Redis ping.
