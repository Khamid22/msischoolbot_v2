# MSI LMS Portal Modules

Status: planning document. Do not treat this as implemented code.

## Current Module Map

Current branch folders:

```text
backend/
  server.py
  routes/
  roles/
  domains/
  identity/
  security/
  utils/
  static/

database/
  database.py
  tables.py
  queries/
  cross_queries/
  academics/
  alembic/

frontend/src/
  app/
  shared/
  roles/

tgbot/
  handlers/
  keyboards/
  helpers.py
```

## Current Responsibility Leaks

- `backend/roles/admin` owns too many business areas: students, parents, payments, teachers, resources, academics, support, announcements, and chat.
- `system_admin` and LMS business roles are mixed under the current code name `admin`.
- CEO, support, and academic director modes are partly represented as admin UI modes instead of real workspaces.
- `tgbot` imports backend identity modules directly.
- Payment logic exists, but access restriction policy does not.
- SQL is spread across route modules, services, and query modules.
- Role and permission definitions are duplicated.

## Target Domain Blocks

### Organization

Owns client schools and contracts.

Responsibilities:

- Schools.
- School contacts.
- School contracts.
- B2B billing relationship.
- Future school settings.

Current schools:

- School 5.
- Sehriyo.

### People

Owns people and account-facing profiles.

Responsibilities:

- Students.
- Parents.
- Teachers.
- Staff profiles.
- Parent-child links.
- Student login code identity.

Rules:

- Student code is globally unique.
- Parents can have children across schools.
- Teacher can teach multiple subjects.

### Teacher Development

Owns Teacher Academy development.

Responsibilities:

- Teacher academy.
- Training assignments.
- Evaluations.
- Promotion decisions.

### Academic Structure

Owns what is taught and how groups are organized.

Responsibilities:

- Subjects.
- Subject programs.
- Program items.
- Groups/classes.
- Enrollments.
- Teacher assignments.
- Schedule rules.

Rule:

- Students do not choose subjects themselves.
- Academic coordinator/director assigns students to groups and subjects.

### Learning Delivery

Owns actual delivery records.

Responsibilities:

- Lesson sessions.
- Practice sessions.
- Cancelled sessions.
- Attendance.
- Homework.
- Office hours.

### Assessment & Progress

Owns performance calculation and progress views.

Responsibilities:

- Exam results.
- AAP.
- AR.
- EP.
- Ratings.
- Student dashboards.
- Academic progress reports.

Important note:

- Existing duplicate exam keys are not cleaned in the rebuild planning phase.
- They should be investigated later with a report.

### Learning Resources

Owns student and teacher learning materials.

Responsibilities:

- Resource types.
- Resources.
- Resource comments.
- File metadata.
- Future storage integration.

### Operations

Owns operational business processes.

Responsibilities:

- Payments.
- Invoices.
- Payment agreements.
- Payment warnings.
- Access restrictions.
- Audit events.
- System settings.

### Communication & Support

Owns communication between parents, students, support, and staff.

Responsibilities:

- Support tickets.
- Ticket messages.
- Parent follow-up.
- Student contact messages.
- Announcements.
- Warnings.

Customer Support scope:

- B2C support only.
- Parents.
- Payments.
- Warnings.
- Follow-up.
- Support tickets.
- No direct academic structure changes by default.

### Analytics & Reports

Owns read models for leaders.

Responsibilities:

- CEO dashboards.
- Company visibility.
- School performance.
- Subject performance.
- Teacher summaries.
- Parent/payment summaries.
- Exam and progress summaries.

CEO visibility:

- Students.
- Teachers.
- Parents.
- Subjects.
- Exams.
- Payments.
- Operations.

Default CEO dashboards can be aggregated, but drilldown is allowed with audit logging.

## Target Workspace Modules

### `system_admin`

Internal system operator.

Responsibilities:

- User recovery.
- Technical settings.
- Diagnostics.
- Migration/admin tooling.
- Emergency data repair after approval.

Not an LMS business role.

### `ceo`

Company leadership workspace.

Responsibilities:

- Aggregated company overview.
- School and subject drilldowns.
- Payments and operations visibility.
- B2B unpaid contract escalation.
- Audit-backed sensitive drilldown.

### `academic_director`

Full academic access for v1.

Responsibilities:

- Academic structure.
- Groups/classes.
- Subject programs.
- Lessons.
- Attendance/homework/exams.
- Teacher academic performance.
- Student academic progress.

### `customer_support`

B2C support workspace.

Responsibilities:

- Parents.
- Payments.
- Warnings.
- Follow-up.
- Support tickets.

Restrictions:

- Should not directly change academic structure by default.
- B2B unpaid school contract issues escalate to CEO only.

### `teacher`

Teacher workspace.

Responsibilities:

- Assigned groups.
- Attendance entry.
- Homework entry.
- Exam entry where allowed.
- Office hours.
- Resources.

Rules:

- Login format is `TCH0001`.
- One account per teacher.
- Teacher can teach multiple subjects.

### `student`

Student workspace.

Responsibilities:

- Own dashboard.
- Attendance.
- Homework.
- Exams.
- Resources.
- Office hours.
- Support/contact flows where allowed.

Rules:

- Login with globally unique MSI code plus password.

### `parent`

Parent workspace.

Responsibilities:

- Linked children across schools.
- Child progress.
- Child attendance/homework/exams.
- Payment status.
- Support tickets.

Rules:

- Telegram-first for first rebuild.
- Password login can be added later.

## Module Dependency Rules

Allowed:

```text
workspace -> domain -> repository -> PostgreSQL
integration -> domain -> repository -> PostgreSQL
frontend -> HTTP API -> backend
```

Forbidden:

```text
tgbot -> backend web routes
backend -> tgbot
frontend -> Python modules
route function -> raw SQL for complex business workflows
```

## Current To Target Mapping

| Current area | Target owner |
|---|---|
| `backend/roles/admin/routes/payment_routes.py` | Operations / Payments |
| `backend/roles/admin/routes/academic_routes.py` | Academic Structure + Learning Delivery |
| `backend/roles/admin/routes/student_routes.py` | People + Academic Structure |
| `backend/roles/admin/routes/parent_routes.py` | People + Communication & Support |
| `backend/roles/admin/routes/teacher_routes.py` | Staff & Hiring + People |
| `backend/roles/parent/routes.py` | Parent workspace + People |
| `backend/domains/academics/*` | Academic Structure, Delivery, Assessment |
| `backend/domains/payments/service.py` | Operations / Payments |
| `tgbot/handlers/start.py` | Telegram integration adapter |
