# models

Shared Pydantic models: the domain objects and request/response schemas that services and
registrators pass between each other. [`user_details/user_details.py`](user_details/user_details.py)
is the caller identity. MCP primitives build it from headers; services receive the object.

## Table of Contents

- [Belongs here](#belongs-here)
- [Does not belong here](#does-not-belong-here)
- [Conventions](#conventions)

## Belongs here

- Domain models that more than one component uses.
- Request and response bodies for the routes.
- Enums and value objects those models are built from.

## Does not belong here

- Configuration models — those live in [`config/`](../config/README.md).
- Store-specific mappings. Keep the persisted shape separate from the models the API speaks, so a
  stored-field rename is not automatically a breaking API change.
- Anything that performs I/O. Models are data plus validation, nothing else.

## Conventions

- One concept per file, named after the concept in `snake_case`.
- Grouped into a subdirectory per domain, named after that domain, rather than left flat. Nesting
  does not shorten the filename: `k8s_probes/k8s_probe_response.py`. Each domain package
  re-exports its models from `__init__.py`, so callers write
  `from app.models.k8s_probes import K8sProbeResponse` rather than the leaf path.
- Field names are `snake_case`. The `ALL_CAPS` convention is specific to config models, where the
  names double as environment variable names.
- Put validation in the model rather than in the caller, and prefer Pydantic's built-in constraints
  over hand-written checks.
- The class Google docstring (including `Attributes:`) is for developers reading the
  code. Customer-facing field copy lives on `Field(description=...)`. Probe bodies
  are the model's dumped JSON, not a generated OpenAPI document.
