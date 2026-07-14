# Engineering Architecture

Audience: engineers changing runtime code.

## Dependency Rule

```text
application
  -> workspace or internal-operations adapter
    -> domain service/public contract
      -> same-domain repository
        -> backend.core.database
          -> PostgreSQL
```

Allowed:

- adapters call public domain services/contracts;
- a service calls repositories in its own product domain;
- a service calls another domain through a public `contracts.py` or service contract;
- reporting consumes explicit read contracts;
- repositories execute SQL for tables owned by their domain;
- Alembic owns schema DDL.

Forbidden:

- SQL in applications, workspaces, HTTP adapters, services, or UI code;
- importing another product domain's repository;
- runtime `CREATE`, `ALTER`, or `DROP` statements;
- reintroducing generic backend technical-layer trees or `features/management`;
- using browser state or role-profile password hashes as an authorization source.

## Composition Boundaries

`backend/application` registers pages/APIs and system endpoints. `backend/workspaces` and `backend/internal_operations` translate HTTP into calls to domain services. They do not own business rules or persistence.

Core is divided by infrastructure responsibility: `core/access`, `core/api`, `core/runtime`, `core/web`, and `core/database.py`. Password and portal-session behavior is Identity-owned. The remaining `core/web/request_context.py` is an explicit compatibility boundary for older form routes, not the pattern for new FastAPI code.

Internal Operations is divided into `pages`, `academics`, `people`, `staffing`, `resources`, `finance`, and `support`. Its academic API is assembled from focused class, group, curriculum, timetable, and gradebook route modules. Product modules and role workspaces must not import Internal Operations; shared invalidation belongs to Platform.

`backend/modules` is organized by product ownership. Academics is subdivided because scheduling, gradebook, curriculum, and assessment rules change independently, while remaining one transaction-capable module. Schedule changes, cancellation/recovery, and holiday reflow retain their existing explicit transaction boundaries.

`backend/platform` contains technical integrations (Redis, object storage, Telegram verification). It does not own LMS business state.

## Public Contracts

- `backend.modules.organization.contracts` exposes organization lookup contracts.
- `backend.modules.people.teachers.contracts` exposes teacher lookup contracts.
- `backend.modules.reporting.academic_contract` is the reporting-facing academic read contract.
- Workspace APIs remain transport adapters, never reusable business owners.

Package `__init__.py` files describe ownership only; they do not form broad import barrels. Callers import the focused service or contract they need.

## Persistence and Transactions

PostgreSQL schema `msi_v2` remains unchanged. Each table has one documented owner in the module map. Cross-domain writes are coordinated through services, not by reaching into a foreign repository. Multi-step academic operations retain row locks and a single transaction so IDs and recorded academic data remain attached to their original lesson sessions.

## Frontend Boundaries

Workspaces compose domain features. `shared` is restricted to cross-domain API, UI, time, motion, and formatting primitives. Teacher Recruitment is owned by `modules/hr/recruitment` and hands accepted records to the separate Teacher Academy or active-teacher domains without provisioning accounts. Internal System Admin composition lives under `internal_operations`, not a reusable business feature.

Large stateful screens are progressively decomposed through focused model, calculation, modal, and calendar modules. Temporary size exceptions are listed in the module map and guarded from further growth; they are not permission to create new catch-all components.

## Future Capabilities

Observations, interventions, payroll, and complete finance workflows are product roadmap items. They are documented rather than represented by empty packages.
