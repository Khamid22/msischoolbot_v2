# Payme Merchant Operations

## Configuration

Configure Payme only through server-side environment variables:

| Variable | Purpose |
|---|---|
| `PAYME_ENVIRONMENT` | `test` or `production` |
| `PAYME_MERCHANT_ID` | Checkout merchant identifier |
| `PAYME_MERCHANT_LOGIN` | HTTP Basic login used by Payme |
| `PAYME_MERCHANT_KEY` | HTTP Basic secret; never sent to the browser |
| `PAYME_CHECKOUT_URL` | Optional hosted-checkout override |
| `PUBLIC_BASE_URL` | Public HTTPS portal origin used for the display callback |
| `PAYME_REQUEST_BODY_MAX_BYTES` | JSON-RPC request limit; defaults to 64 KiB |
| `PAYME_TRANSACTION_TIMEOUT_SECONDS` | Create-to-perform limit; defaults to 12 hours |

`PAYME_MERCHANT_KEY` is redacted from settings representations. Production application mode refuses
to enable a test Payme configuration. Test and production credentials must be managed separately in
the deployment platform and must not be committed.

## Trust Boundary

- Payme calls `POST /api/v1/integrations/payme/merchant`.
- HTTP Basic credentials authenticate the provider request.
- `account[invoice_id]` is the only checkout account field.
- The browser callback only returns the parent to the admission status page.
- Only `PerformTransaction` confirms an invoice payment.
- The provider amount must equal the invoice's remaining UZS balance in tiyin.
- A contract must be accepted and every reserved group must still be active.
- A pending Payme transaction blocks manual settlement of the same invoice.

Every provider state transition and admission activation is committed in one PostgreSQL transaction.
Repeated provider requests return the persisted result instead of creating another payment.

## Sandbox Release Checklist

1. Apply the additive admission migration to an isolated staging database.
2. Configure test credentials in the staging runtime; do not put them in source or frontend variables.
3. Exercise authentication failure and every required Merchant API method.
4. Exercise wrong amount, expired transaction, duplicate create/perform/cancel, and `GetStatement`.
5. Confirm that a completed transaction creates one invoice payment and one active admission.
6. Confirm that an activation failure rolls back the payment and Payme transaction state.
7. Confirm that manual settlement is rejected while Payme is pending.
8. Confirm cancellation before service start returns the admission to `awaiting_payment`.
9. Confirm cancellation after service start moves the admission to `payment_review`.
10. Replace any previously shared test key before enabling access beyond the sandbox team.

Production credentials should be enabled only after the Payme sandbox suite and reconciliation
statement have passed.
