import { useMemo, useState, type FormEvent } from "react";
import { Check, KeyRound, LogOut, ShieldCheck } from "lucide-react";
import { apiData, apiErrorMessage, apiSend, apiSucceeded } from "@/shared/lib/api";

interface AccountSecurityProps {
  login?: string;
  role?: string;
  mustChangePassword?: boolean;
  passwordApiUrl?: string;
  continueUrl?: string;
  logoutUrl?: string;
}

type PasswordResult = {
  changed?: boolean;
  must_change_password?: boolean;
  session_version?: number;
};

export default function AccountSecurity(props: AccountSecurityProps) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [changed, setChanged] = useState(false);

  const checks = useMemo(
    () => [
      { label: "At least 8 characters", met: newPassword.length >= 8 },
      { label: "Different from your current password", met: Boolean(newPassword) && newPassword !== currentPassword },
      { label: "Confirmation matches", met: Boolean(confirmPassword) && confirmPassword === newPassword },
    ],
    [confirmPassword, currentPassword, newPassword],
  );

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting || !checks.every((check) => check.met)) return;
    setSubmitting(true);
    setError("");
    try {
      const response = await apiSend(props.passwordApiUrl || "/api/v1/auth/password", "PATCH", {
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      const payload: unknown = await response.json();
      if (!apiSucceeded(response, payload)) {
        setError(apiErrorMessage(payload, "Could not change your password."));
        return;
      }
      const result = apiData<PasswordResult>(payload);
      setChanged(Boolean(result.changed));
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch {
      setError("Network error. Check your connection and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  const roleLabel = String(props.role || "account").replace(/_/g, " ");

  return (
    <main className="app-min-height safe-x safe-y flex items-center justify-center bg-background">
      <section className="w-full max-w-lg overflow-hidden rounded-2xl border border-foreground/10 bg-surface shadow-card">
        <div className="border-b border-foreground/8 bg-primary px-5 py-5 text-primary-foreground sm:px-7">
          <div className="flex items-start gap-3">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/12">
              <ShieldCheck className="h-6 w-6" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <h1 className="font-display text-xl font-bold">Secure your account</h1>
              <p className="mt-1 text-sm text-primary-foreground/80">
                {props.mustChangePassword
                  ? "Your initial password matches your login. Choose a private password to continue."
                  : "Update your password whenever you need to protect your portal access."}
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-5 px-5 py-5 sm:px-7 sm:py-6">
          <div className="grid gap-2 rounded-xl border border-foreground/8 bg-muted/60 px-4 py-3 text-sm sm:grid-cols-2">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Login</p>
              <p className="mt-0.5 truncate font-mono font-bold">{props.login || "—"}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Role</p>
              <p className="mt-0.5 font-semibold capitalize">{roleLabel}</p>
            </div>
          </div>

          {changed ? (
            <div role="status" className="rounded-xl border border-success/25 bg-success/10 px-4 py-4 text-success">
              <div className="flex items-center gap-2 font-bold">
                <Check className="h-5 w-5" aria-hidden="true" />
                Password changed successfully
              </div>
              <p className="mt-1 text-sm text-foreground/75">Your current session is secure and ready to continue.</p>
              <a
                href={props.continueUrl || "/"}
                className="mt-4 inline-flex min-h-11 w-full items-center justify-center rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-primary-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                Continue to portal
              </a>
            </div>
          ) : (
            <form onSubmit={submit} className="space-y-4">
              {error ? (
                <p role="alert" className="rounded-xl border border-destructive/20 bg-destructive/10 px-3 py-2.5 text-sm font-semibold text-destructive">
                  {error}
                </p>
              ) : null}

              <PasswordField
                label="Current password"
                autoComplete="current-password"
                value={currentPassword}
                onChange={setCurrentPassword}
              />
              <PasswordField
                label="New password"
                autoComplete="new-password"
                value={newPassword}
                onChange={setNewPassword}
              />
              <PasswordField
                label="Confirm new password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={setConfirmPassword}
              />

              <ul className="space-y-1.5" aria-label="Password requirements">
                {checks.map((check) => (
                  <li key={check.label} className={`flex items-center gap-2 text-xs font-semibold ${check.met ? "text-success" : "text-muted-foreground"}`}>
                    <span className={`flex h-4 w-4 items-center justify-center rounded-full border ${check.met ? "border-success bg-success text-success-foreground" : "border-foreground/20"}`}>
                      {check.met ? <Check className="h-3 w-3" aria-hidden="true" /> : null}
                    </span>
                    {check.label}
                  </li>
                ))}
              </ul>

              <button
                type="submit"
                disabled={submitting || !checks.every((check) => check.met)}
                className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-primary-foreground shadow-card transition-transform active:translate-y-px disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none"
              >
                <KeyRound className="h-4 w-4" aria-hidden="true" />
                {submitting ? "Saving…" : "Change password"}
              </button>
            </form>
          )}

          <form action={props.logoutUrl || "/logout"} method="post">
            <button
              type="submit"
              className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-foreground/12 bg-background px-4 py-2.5 text-sm font-semibold text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              <LogOut className="h-4 w-4" aria-hidden="true" />
              Sign out
            </button>
          </form>
        </div>
      </section>
    </main>
  );
}

function PasswordField({
  label,
  value,
  autoComplete,
  onChange,
}: {
  label: string;
  value: string;
  autoComplete: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</span>
      <input
        type="password"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        autoComplete={autoComplete}
        required
        className="min-h-11 w-full rounded-xl border-2 border-foreground/10 bg-background px-3.5 py-2.5 text-base outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/15"
      />
    </label>
  );
}
