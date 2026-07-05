# MSI LMS Portal Telegram Parent Linking

Status: planning document. Do not treat this as implemented code.

## Core Decisions

- Parents are Telegram-first for the first rebuild.
- Parent password login can be added later.
- Parents are linked through generated student invite link plus Telegram bot/Mini App.
- A parent can have children across schools.
- PostgreSQL is the source of truth for parent identity and links.

## Current Flow

Current working flow:

1. Staff creates parent invite for a student.
2. Backend creates signed token and short invite code.
3. Telegram deep link uses `parent_{code}` start parameter.
4. Bot receives `/start parent_{code}`.
5. Bot attempts to link parent from Telegram profile.
6. Bot opens Mini App invite URL.
7. Web validates invite and Telegram initData.
8. Parent record is created or updated.
9. `parent_student_links` row is created.
10. Parent session is created.
11. Parent sees linked children only.

## Target Flow

Target parent linking should be owned by a shared domain service.

```text
CEO, Academic Director, or Customer Support
  -> create parent invite
  -> account_invites row
  -> Telegram deep link
  -> bot or Mini App
  -> validate invite
  -> validate Telegram identity
  -> create/update parent
  -> create parent_student_link
  -> audit event
```

Bot and web should call the same parent-link service.

Confirmed invite generators:

- CEO.
- Academic Director.
- Customer Support.

## Data Model

Recommended tables:

- `parents`
- `parent_student_links`
- `account_invites`
- `account_telegram_links`
- `telegram_accounts`
- `audit_events`

### `parents`

Stores parent profile:

- display name.
- phone.
- Telegram username.
- preferred language.
- status.

### `parent_student_links`

Stores parent-child relationship:

- parent id.
- student id.
- relationship.
- status.
- created at.

This table supports many-to-many links.

### `account_invites`

Stores invite lifecycle:

- invite type: `parent`.
- token hash or invite code hash.
- signed payload reference.
- target student id.
- issued by staff id.
- expires at.
- max uses.
- used count.
- status.
- used by Telegram user id.
- created at.
- used at.

### `telegram_accounts`

Stores Telegram identity:

- Telegram user id.
- username.
- first name.
- last name.
- created at.
- updated at.

### `account_telegram_links`

Stores durable Telegram-to-account link when the target account model is introduced.

## Invite Lifecycle

Statuses:

- `pending`
- `used`
- `expired`
- `revoked`

Rules:

- Invite must expire.
- Invite must be signed or stored with hashed token/code.
- Invite should identify the target student.
- Invite should record issuing staff.
- Invite use should be auditable.

## Security Rules

- Never trust a raw Telegram user id from the client.
- Verify Telegram Mini App initData HMAC.
- Signed invite token alone is not a Telegram identity proof.
- Parent can access only linked students.
- Parent-child link changes require audit events.
- Unlink actions must remove access immediately.

## Parent Cross-School Support

The parent portal should not assume one school.

Rules:

- A parent can link to School 5 child and Sehriyo child at the same time.
- Parent home should group or label children by school.
- Payment, progress, and support data must be filtered per linked child.

## Manual Fallback

Current flow has manual form fallback.

Target rule:

- Keep manual fallback only if operationally needed.
- Manual fallback should still create an audited parent profile and link.
- Manual fallback should not bypass parent-child access checks.

## Bot Responsibilities

Telegram bot should:

- receive `/start parent_{code}`.
- record/update Telegram account.
- call parent-link domain service.
- open Mini App.
- show simple status messages.

Telegram bot should not:

- own database rules.
- import web route modules.
- duplicate parent-link SQL.

## Web Responsibilities

Web Mini App should:

- verify invite.
- verify Telegram initData.
- call parent-link domain service.
- create session.
- route parent to parent workspace.

Web should not:

- trust unsigned identity fields.
- allow parent access without link check.

## Parent Workspace Access

Parent access is computed by:

```text
parent_id + student_id -> active parent_student_links row
```

No linked row means no access.

## Future Parent Password Login

Password login is deferred.

When added later:

- parent still maps to the same parent profile.
- Telegram link remains valid.
- password account must not create duplicate parent identities.
- parent still sees only linked children.
