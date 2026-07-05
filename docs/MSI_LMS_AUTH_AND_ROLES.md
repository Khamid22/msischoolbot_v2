# MSI LMS Portal Auth And Roles

Status: planning document. Do not treat this as implemented code.

## Core Decisions

- One user has one role.
- Admin is an internal system operator, not an LMS business role.
- Documentation uses `system_admin`.
- Current code may temporarily still use `admin`.
- Students log in with MSI code plus password.
- Teachers log in with `TCH0001` format.
- Parents are Telegram-first for first rebuild.
- Parent password login can be added later.

## Real LMS Roles

The LMS business roles are:

- `ceo`
- `hr_manager`
- `customer_support`
- `student`
- `teacher`
- `parent`
- `academic_director`

Internal platform role:

- `system_admin`

## Role Purposes

### `system_admin`

Internal system operator.

Responsibilities:

- Technical settings.
- User recovery.
- Migration support.
- Diagnostics.
- Emergency repair after approval.

Not responsible for normal LMS business operations.

### `ceo`

Company leadership.

Access:

- Broad visibility across students, teachers, parents, subjects, exams, payments, and operations.
- Aggregated dashboards by default.
- Drilldown allowed with audit logging.
- B2B unpaid school contract escalation.

### `academic_director`

Academic leadership.

Access:

- Full academic access for v1.
- Subjects, programs, groups, enrollments, lessons, attendance, homework, exams, progress, and teacher academic performance.

### `hr_manager`

Hiring and teacher development.

Access:

- Teacher candidates.
- Hiring pipeline.
- Teacher academy.
- Training evaluations.

### `customer_support`

B2C support.

Access:

- Parents.
- Payments.
- Warnings.
- Follow-up.
- Support tickets.

Restrictions:

- Should not directly change academic structure by default.
- Should not resolve B2B unpaid school contract issues directly.
- B2B unpaid contract issues escalate to CEO only.

### `teacher`

Teaching role.

Rules:

- One account per teacher.
- Login format: `TCH0001`.
- Teacher can teach multiple subjects.

Access:

- Assigned groups.
- Assigned students.
- Attendance and homework entry where permitted.
- Exam entry where permitted.
- Office hours.
- Teaching resources.

### `student`

Learner role.

Rules:

- Login with globally unique MSI code plus password.
- Student code should be globally unique.

Access:

- Own academic dashboard.
- Attendance.
- Homework.
- Exams.
- Resources.
- Support/contact flows where allowed.

### `parent`

Guardian role.

Rules:

- Telegram-first for first rebuild.
- Can be linked to multiple children.
- Children can be across schools.
- Password login can be added later.

Access:

- Linked children only.
- Child progress.
- Child attendance/homework/exams.
- Payment status.
- Support tickets.

## Login Identifiers

| Role | Login |
|---|---|
| Student | globally unique MSI student code |
| Teacher | `TCH0001`, `TCH0002`, etc. |
| Parent | Telegram identity in v1 |
| CEO/HR/Support/Academic Director | staff account login |
| System Admin | internal operator login |

## Session Model

Target session data should contain:

- `account_id`
- `role`
- role-specific profile id, when needed
- `telegram_user_id`, when linked
- session creation timestamp
- last activity timestamp

Avoid storing broad business state in session. Use PostgreSQL for durable state.

## Authorization Model

Use two checks:

1. Role check: can this role enter this workspace?
2. Policy check: can this user perform this action on this object?

Examples:

- Parent can view only linked children.
- Teacher can manage only assigned groups.
- Customer Support can manage B2C support records but not academic structure.
- Customer Support can request B2C access restrictions from CEO or Academic Director.
- Customer Support cannot approve B2C access restrictions directly.
- CEO can drill down, but sensitive drilldown should create audit events.
- Access restrictions are evaluated through policy, not hardcoded in routes.

## Target Permission Areas

Permission areas:

- `organization.view`
- `organization.manage_contracts`
- `people.view`
- `people.manage_students`
- `people.manage_parents`
- `people.manage_teachers`
- `academic.view`
- `academic.manage`
- `delivery.manage`
- `assessment.manage`
- `payments.view`
- `payments.manage`
- `support.manage`
- `hr.manage`
- `reports.view`
- `system.manage`

The exact permission table can be introduced after workspace boundaries are clear.

## Migration From Current `admin`

Current code uses `admin` for:

- internal operator work,
- broad management UI,
- preview shells for business roles.

Target split:

- `system_admin` gets internal technical operations.
- `ceo`, `academic_director`, `hr_manager`, and `customer_support` get real workspaces.
- Shared UI components can remain, but access must be enforced by role and policy.

## Audit Requirements

Audit these actions:

- CEO sensitive drilldowns.
- Payment changes.
- Payment warning creation.
- Access restriction creation/removal.
- Parent-child linking/unlinking.
- Student password resets.
- Teacher account creation.
- Academic structure changes.
- Data imports.

## First Rebuild Scope

Implement first:

- One shared `accounts` table for all login identities.
- One-role account model.
- Separate role-specific profiles/domain rows.
- Student MSI code login.
- Teacher `TCH0001` login.
- Telegram-first parent login.
- Real workspaces for CEO, Academic Director, HR, Customer Support, Teacher, Student, Parent, and System Admin.

Do not implement parent password login in v1.
