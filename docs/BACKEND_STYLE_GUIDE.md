# Backend Style Guide

This guide is the implementation contract for new and migrated backend code.
Existing compatibility modules may temporarily differ, but they must not grow.

## Module shape

Business capability and person orchestration are separate:

```text
backend/modules/
├── people/<person>/             actor-specific orchestration and default scope
│   └── workspace/               that person's HTTP/page adapters
├── domains/<domain>/            reusable rules, contracts, and persistence
└── jobs/                        durable outbox infrastructure
```

Person modules declare a `PersonModuleSpec` in `module.py`, never import another
person module, and consume only their allowed domains through public contracts.
Their `workspace/` package calls the surrounding person's contract and contains
no business rules, SQL, or transaction commits.

Small product modules use:

```text
module.py
api.py
schemas.py
contracts.py
domain_types.py
policies.py
catalog.py
commands.py
queries.py
repository.py
events.py
```

Split `commands.py` or `queries.py` by business capability after eight use cases
or roughly 500 lines. Do not create new generic `service.py`, `common.py`,
`helpers.py`, or `utils.py` files.

Transport parses and renders. Commands mutate. Queries read. Policies decide.
Repositories own SQL. Cross-module callers use `contracts.py`, never another
module's repository.

## Naming

- Python uses `snake_case`; classes and typed command/results use `PascalCase`.
- External JSON may use `camelCase` through `ApiModel` aliases.
- Use `get_` for one required object, `find_` for an optional repository result,
  `list_` for collections, and `search_` for filtered collections.
- Use `create_`, `update_`, `archive_`, and `delete_` according to lifecycle
  semantics. `ensure_` is reserved for idempotent create-or-repair behavior.
- Boolean names start with `is_`, `has_`, or `can_`.
- Identifiers include their entity name, such as `candidate_id`.

## Constants

- Stable domain values use `StrEnum` in `domain_types.py`.
- Business thresholds belong to `policies.py`.
- Labels and ordering belong to `catalog.py`.
- Deployment values belong to typed runtime settings.
- Per-school or administrator-editable values belong in PostgreSQL.
- A single-use implementation detail may remain a well-named local constant.

Do not extract obvious arithmetic values such as zero or one merely to eliminate
all literals. Name values whose purpose is otherwise unclear or whose meaning is
shared.

## Size and types

New or touched application modules target 500 lines, repositories target 700
lines, functions target 60 lines, and cyclomatic complexity targets 12.
Public module interfaces are typed and do not expose `dict[str, Any]`. Convert
database rows into Pydantic models, dataclasses, or `TypedDict` before crossing a
module boundary.
