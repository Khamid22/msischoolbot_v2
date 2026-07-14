# Internal Operations

This package is the protected system-admin transport adapter. It owns HTTP routing and page composition; it does not own product rules or SQL.

```text
internal_operations/
├── api_router.py                 # Assembles `/api/v1/admin` routers
├── form_routes.py                # Assembles legacy HTML form routes
├── pages/
│   ├── routes.py                 # `/internal/operations` page routes
│   ├── context.py                # Page bootstrap orchestration
│   └── options.py                # School/resource selector builders
├── academics/
│   ├── routes.py                 # Academic router assembly
│   ├── class_routes.py
│   ├── group_routes.py
│   ├── curriculum_routes.py
│   ├── timetable_routes.py
│   ├── gradebook_routes.py
│   ├── office_hours_routes.py
│   └── form_routes.py
├── people/
│   ├── students/                 # Student API, forms, and contracts
│   └── parents/                  # Parent API and contracts
├── staffing/                     # Teacher and recruitment form routes
├── resources/                    # Learning-resource API and forms
├── finance/                      # Payment API and contracts
└── support/                      # Complaint API and contracts
```

Rules:

- Route files validate transport input and call domain services.
- Product behavior belongs in `backend/modules`.
- Runtime SQL belongs in the owning module repository.
- Product modules and role workspaces must never import this package.
- Shared cache invalidation lives in `backend/platform/admin_page_cache.py`.
- Existing URLs and response payloads remain stable when adapters are reorganized.
