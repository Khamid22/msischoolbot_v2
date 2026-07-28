import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";

function source(relativePath: string) {
  return readFileSync(
    new URL(relativePath, import.meta.url),
    "utf8",
  );
}

describe("Student billing enforcement workspace", () => {
  it("registers dedicated payment and support pages", () => {
    const app = source("../../app/App.tsx");
    assert.match(app, /"student-payments"/);
    assert.match(app, /"student-support"/);
  });

  it("keeps payment and support available in the mobile account navigation", () => {
    const shell = source("./StudentAccountShell.tsx");
    assert.match(shell, /\/student\/payments/);
    assert.match(shell, /\/student\/support/);
    assert.match(shell, /var\(--app-bottom-inset\)/);
    assert.match(shell, /min-h-12/);
  });

  it("submits only invoice identifiers and amount to Payme checkout", () => {
    const payments = source("./pages/Payments.tsx");
    assert.match(payments, /account\[invoice_id\]/);
    assert.match(payments, /checkout\.amountMinor/);
    assert.doesNotMatch(payments, /merchantKey|merchant_key|PAYME_KEY/);
  });

  it("provides a real support ticket create and reply flow", () => {
    const support = source("./pages/Support.tsx");
    assert.match(support, /\/support\/tickets/);
    assert.match(support, /\/messages/);
    assert.match(support, /status !== "resolved"/);
  });
});
