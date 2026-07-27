# Person Module Ownership

When a task names one person, keep the change inside that person's ownership
boundary unless the task explicitly expands the scope.

## Default change scope

For `<person>`, the default writable scope is:

- `backend/modules/people/<person>/**`
- `frontend/src/workspaces/<person>/**`
- Tests dedicated to that person

The Head of Department uses the canonical singular directory
`backend/modules/people/head_of_department/workspace/`.

## Shared domain changes

A person module may use only the domains declared by its `PERSON_MODULE` in
`module.py`. Cross-boundary imports must target the domain's `contracts.py`,
`domain_types.py`, `schemas.py`, or `catalog.py`; repositories are private to
their domain.

An assigned agent may make the smallest necessary change to an allowed
domain's typed contract and implementation. It must not change another person
module or broaden another person's access defaults without explicit scope.

## Dependency direction

```text
workspace -> person contracts -> allowed domain contracts -> repositories
```

- Person modules never import other person modules.
- Domains never import `backend.modules.people`.
- Workspaces and person modules contain no SQL.
- Jobs remain in `backend/modules/jobs` and are created through the outbox.
