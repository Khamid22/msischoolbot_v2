# Repository and Deployment Rules

These rules are mandatory for every AI agent working in this repository.

## Canonical GitHub repository

- Use only `https://github.com/sen-msischool/msischoolv1.git`.
- The expected Git remote name is `msischoolv1`.
- Do not push project changes to `origin` or another repository.
- Always inspect the current branch, worktree, and remote before editing or
  pushing.
- Preserve unrelated tracked and untracked user changes. Stage only files that
  belong to the current task.

## Branch ownership

### LMS application work

Use the `FastAPI-Run-System` branch for general LMS work, including:

- Backend and frontend features.
- People modules and business domains.
- Customer Support, parent, teacher, student, and academic workspaces.
- Shared infrastructure, workers, tests, and documentation.
- Finance behavior that is not specific to a payment provider.

Push LMS work explicitly to:

```text
msischoolv1/FastAPI-Run-System
```

### Payme integration work

Use the `payme-integration` branch for payment-provider work, including:

- Payme Merchant API methods and JSON-RPC behavior.
- Payme authentication, sandbox, checkout URLs, and callbacks.
- Payme transaction persistence and reconciliation.
- Payme-specific Railway variables and configuration.
- Payme-specific tests and documentation.

Shared invoice, billing, parent, or worker changes required by Payme may be
implemented on `payme-integration`, but must not be copied or merged into
`FastAPI-Run-System` without explicit user approval.

Push Payme work explicitly to:

```text
msischoolv1/payme-integration
```

If a task mixes independent LMS and Payme changes, separate the work by branch
and commit. Do not combine unrelated changes in one commit.

## Protected main branch

- Never commit to, push to, merge into, rebase, reset, force-push, delete, or
  change the GitHub `main` branch.
- Never open a pull request targeting `main` unless the user explicitly asks.
- Never use `main` as a temporary branch.
- Read-only comparisons against `main` are allowed only when needed to
  investigate history or verify safety.
- Before every push, print and verify the local branch and the full destination
  ref. Never use an ambiguous `git push`.

## Git delivery rules

- Use Git for every delivered code change.
- Run relevant tests before committing.
- Use a focused, descriptive commit.
- Push with an explicit remote, source branch, and destination branch.
- Never force-push.
- After pushing, verify the remote branch commit SHA.
- Do not stage `.env` files, credentials, local editor settings, generated
  files, or unrelated worktree changes.

# Railway Production Safety

## Allowed environment

- Use only the Railway `production` environment.
- Never deploy to, configure, restart, redeploy, remove, or otherwise mutate
  the Railway `main` environment.
- Never assume the currently linked Railway environment or service is correct.
- Every Railway mutation must explicitly name the `production` environment and
  the intended service.
- Do not use an unqualified deployment command that relies on the current
  Railway CLI context.

## Deployment procedure

Before a Railway change:

1. Verify the Git branch and commit SHA.
2. Verify the Railway environment is `production`.
3. Verify the exact service name and its configured source branch.
4. Confirm that no unrelated service will be redeployed.

After a Railway change:

1. Verify the deployment reached `SUCCESS`.
2. Check the service health endpoint and relevant logs.
3. Confirm the deployed commit SHA.
4. Confirm the other production services remain healthy.

Do not change a Railway service's source repository, source branch, start
command, environment variables, replica count, or domain unless the task
explicitly requires that exact change.

## Production service boundaries

- LMS web and bot changes belong to the production LMS service.
- Durable finance jobs belong to the production finance worker.
- Payme Merchant API changes must be deployed only from approved
  `payme-integration` code.
- Do not point any service at GitHub `main`.
- Do not create, delete, or reconnect a Railway service without explicit user
  approval.

# Data and Secret Safety

- Never delete, truncate, overwrite, or bulk-modify production database records
  without explicit confirmation immediately before the operation.
- Explain the exact records and recovery implications before any destructive
  database action.
- Prefer additive, reversible migrations. Inspect the current Alembic revision
  before applying a migration.
- Do not run a migration containing deletion or destructive data rewriting
  without explicit approval.
- Never commit, print, expose, or log API keys, Telegram tokens, Payme keys,
  database URLs, or other secrets.
- Store Payme sandbox and production credentials only in Railway production
  environment variables, with sandbox and production values kept separate.
- Payment callbacks and browser redirects never confirm a payment; only the
  authenticated Payme Merchant API may confirm a Payme transaction.

# Verification Requirements

- Test the smallest relevant backend and frontend scope first, then broader
  checks in proportion to risk.
- Payment changes require tests for authentication, idempotency, duplicate
  requests, exact amounts, transaction state, cancellation, and reconciliation.
- Worker changes require tests for retries, leases, duplicate delivery, and
  idempotency.
- Database changes require migration validation and rollback/consistency tests.
- Do not claim a push, deployment, notification, or payment succeeded without
  verifying the resulting external state.
- Report the branch, commit SHA, Railway environment, service, tests, and any
  remaining risk at handoff.

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
