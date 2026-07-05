# MSI LMS Portal Payment And Access Policy

Status: planning document. Do not treat this as implemented code.

## Core Decisions

- Payment management is required.
- Payments must use invoices, warnings, agreements, and access restrictions.
- Access restrictions must be controlled by policy.
- Do not hardcode blocking directly in routes.
- Customer Support handles B2C support only.
- B2B unpaid school contract issues escalate to CEO only.
- Do not automatically block a whole school.

## Payment Concepts

### Payment Agreement

Agreement that defines how a student or school should be billed.

For B2C public school families:

- Monthly.
- 3-month.
- Annual.
- Customer Support can define the agreement.

For B2B private school contracts:

- Per school contract.
- Contract issues escalate to CEO.

### Invoice

A billable obligation.

Fields should include:

- payer type: parent, student, or school contract.
- student id, when B2C.
- school contract id, when B2B.
- amount.
- currency.
- due date.
- status.
- created by.
- created at.

### Payment

Actual payment event.

Fields should include:

- invoice id.
- amount.
- paid at.
- method.
- reference.
- recorded by.
- notes.

### Payment Warning

Support workflow record before restriction.

Fields should include:

- invoice id or agreement id.
- student id.
- parent id.
- warning stage.
- message.
- channel.
- sent by.
- sent at.
- response status.
- follow-up date.

### Access Restriction

Audited decision to restrict access or participation.

Fields should include:

- restriction type.
- student id.
- parent id, if applicable.
- reason.
- source invoice id, if applicable.
- policy decision id.
- status.
- starts at.
- ends at.
- created by.
- approved by, if required.
- audit notes.

## Proposed Tables

```text
payment_agreements
invoices
invoice_items
payments
payment_warnings
access_policies
access_policy_decisions
access_restrictions
school_contracts
school_contract_events
```

The current `payments` table can be migrated into the target model later.
There are currently no production payment rows, so payment schema can be fixed before real payment data grows.

## B2C Workflow

B2C means parent/student payment support.

Flow:

1. Agreement exists for student/family.
2. Invoice is generated or created.
3. Due date approaches.
4. Customer Support follows up.
5. If unpaid, incoming payment warning is recorded.
6. If still unpaid, final warning is recorded that only a few days remain before restriction.
7. If still unresolved, Customer Support requests restriction approval from CEO or Academic Director.
8. If approved, access policy creates restriction.
9. Restriction is stored as an auditable row.
10. Routes and class participation checks read the restriction.

The restriction remains active until payment is completed or an authorized approval removes it.

Customer Support can:

- view parent/student payment state.
- create payment warnings.
- record follow-up.
- record parent response.
- request B2C access restrictions from CEO or Academic Director.
- continue B2C work after restriction approval is granted.

Customer Support should not:

- change academic structure by default.
- change B2B school contracts directly.
- hardcode blocks by editing student/group rows randomly.
- approve access restrictions by themselves.

Approval rule:

- CEO or Academic Director approves B2C access restrictions.
- Customer Support can request and then execute the follow-up workflow after approval.

## B2B Workflow

B2B means private school contract payment.

Flow:

1. School contract has unpaid issue.
2. System creates CEO escalation item.
3. CEO reviews contract/payment context.
4. CEO decides business action.

Rules:

- Do not automatically block all students in a school.
- Do not let Customer Support independently enforce B2B contract restrictions.
- If any student-level restriction is needed later, it must come from a CEO-approved policy decision.

## Access Policy Engine

The access policy engine answers:

```text
Can this student perform this action right now?
```

Examples:

- Can enter class.
- Can view student dashboard.
- Can submit homework.
- Can book office hours.
- Can use chat/support.

The policy engine should read:

- active access restrictions.
- payment invoice state.
- warning history.
- agreement type.
- role.
- school contract state.

It should return:

- allowed: true/false.
- reason code.
- user-facing message key.
- audit context.

Routes should not decide payment blocking themselves. Routes should ask the policy engine.

## Restriction Types

Possible restriction types:

- `class_attendance_restricted`
- `dashboard_restricted`
- `office_hours_restricted`
- `chat_restricted`
- `parent_portal_restricted`

For v1, the most important restriction is class attendance/participation.

## Statuses

Invoice statuses:

- `draft`
- `issued`
- `due`
- `overdue`
- `partially_paid`
- `paid`
- `cancelled`

Warning statuses:

- `scheduled`
- `sent`
- `acknowledged`
- `no_response`
- `resolved`
- `escalated`

Restriction statuses:

- `pending`
- `active`
- `paused`
- `resolved`
- `cancelled`

## Audit Requirements

Audit:

- invoice creation/update/delete.
- payment recording.
- warning creation.
- warning status update.
- access restriction creation.
- access restriction activation.
- access restriction removal.
- CEO B2B escalation action.

## UI Requirements

Customer Support workspace:

- parent lookup.
- student payment state.
- invoice list.
- warning timeline.
- follow-up tasks.
- support ticket link.

CEO workspace:

- B2B contract escalation queue.
- school payment summary.
- drilldown with audit logging.

Parent workspace:

- own linked child payment state.
- invoice history.
- support contact.

Student workspace:

- clear restriction message only when policy restricts an action.

## Implementation Rule

Do not implement random checks like:

```text
if unpaid: block route immediately
```

Instead:

```text
decision = access_policy.can(student, action)
```

The decision must come from the policy domain and be backed by PostgreSQL state.
