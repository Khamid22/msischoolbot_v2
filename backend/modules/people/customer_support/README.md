# Customer Support Backend

Customer Support is a person module. It owns actor-specific orchestration and
authorization, but it does not own business tables or SQL.

```text
customer_support/
├── module.py                 person defaults and per-section dependencies
├── domain_types.py           stable workspace vocabulary
├── policies.py               role, capability, and school-scope guards
├── scope.py                  typed current-assignment scope resolver
├── contracts.py              compatibility facade for current callers
├── dashboard/
│   ├── contracts.py
│   └── queries.py
├── parents/
│   ├── contracts.py
│   ├── commands.py
│   └── queries.py
├── teachers/
│   ├── contracts.py
│   ├── queries.py
│   └── schemas.py
├── tickets/
│   ├── contracts.py
│   ├── commands.py
│   └── queries.py
└── workspace/
    ├── api.py                current FastAPI compatibility adapter
    ├── page.py
    └── teachers_api.py       completed read-only teacher transport
```

## Domain ownership

| Customer Support section | Reusable domain owners |
| --- | --- |
| Dashboard | `reporting/customer_support` |
| Parents | `parent_relationships`, `student_records`, `identity`, `finance`, `support_cases` |
| Teachers | `teacher_records`, `identity`, `organization`, `support_cases` |
| Tickets | `support_cases/tickets`; contextual people data comes through typed domain contracts |

All reads and writes remain restricted to the actor's assigned schools. The
Teachers section is read-only by default. `manage_teacher_access` is an
available capability but is deliberately not part of Customer Support defaults.
The implemented Teachers directory supports scoped search, status and school
filters, cursor pagination, and read-only account, school, subject, and group
details. It exposes only `GET` routes and has no mutation contract.

## Integration sequence

1. Keep the existing `/api/v1/customer-support` responses as characterization
   tests while new contracts are implemented.
2. Implement scoped parent readers behind their domain contracts. The scoped
   Teacher Records reader and Customer Support teacher transport are complete.
3. Implement the ticket queue repository with explicit school scope and cursor
   pagination; do not expose the unscoped compatibility functions to the new API.
4. Implement the dashboard projections and connect
   `GetCustomerSupportDashboard`.
5. Add one transport router per completed section and include it from
   `workspace/api.py`.
6. Move existing parent operations out of
   `support_cases/customer_records_service.py` behind their owning domain
   commands, leaving temporary compatibility exports.
7. Remove compatibility exports only after route snapshots and frontend
   contracts have migrated.

The folders in this package are executable boundaries, not independent
deployments. A section may call only its declared domain contracts and may not
import another person module, a domain repository, or another section's private
implementation.
