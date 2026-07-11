import { Home, ShieldAlert } from "lucide-react";

interface UnauthorizedProps {
  authRole?: string;
  roleDisplayName?: string;
  message?: string;
}

export function Unauthorized({
  authRole = "",
  roleDisplayName = "",
  message = "This workspace is not available for your role.",
}: UnauthorizedProps) {
  return (
    <main className="flex min-h-[var(--tg-viewport-height)] items-center justify-center bg-background px-4 py-8 text-foreground">
      <section className="w-full max-w-md rounded-2xl border border-border bg-surface p-6 text-center shadow-card">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-50 text-amber-600">
          <ShieldAlert className="h-6 w-6" />
        </div>
        <p className="mt-4 text-xs font-bold uppercase tracking-wide text-muted-foreground">
          MSI School
        </p>
        <h1 className="mt-2 text-2xl font-black text-foreground">Workspace unavailable</h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">{message}</p>
        {roleDisplayName || authRole ? (
          <p className="mt-3 rounded-xl bg-muted px-3 py-2 text-xs font-bold text-muted-foreground">
            Current role: {roleDisplayName || authRole}
          </p>
        ) : null}
        <a
          className="mt-5 inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-bold text-primary-foreground shadow-sm transition-transform active:scale-[0.98]"
          href="/"
        >
          <Home className="h-4 w-4" />
          Return home
        </a>
      </section>
    </main>
  );
}

export default Unauthorized;
