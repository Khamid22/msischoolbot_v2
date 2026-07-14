import { GraduationCap, KeyRound, LogOut } from "lucide-react";
import { AcademyTeacherPreview } from "@/features/reporting/overview/RoleOverviewPanel";
import { routes } from "@/shared/lib/routes";

type TeacherHomeProps = {
  authLogin?: string;
  academyTeacher?: Record<string, unknown> | null;
  csrfToken?: string;
};

/**
 * Read-only landing for a signed-in academy teacher: their own Teacher Academy
 * profile (progress, appointed lessons, assessment reports), plus links to change
 * their password and log out. Reuses the AcademyTeacherPreview admins see under
 * "Preview as Teacher".
 */
export default function TeacherHome({ authLogin = "", academyTeacher = null, csrfToken = "" }: TeacherHomeProps) {
  return (
    <main className="min-h-[var(--tg-viewport-height)] bg-background text-foreground">
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-2.5">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-sidebar text-white">
              <GraduationCap className="h-5 w-5" />
            </span>
            <div className="min-w-0 leading-tight">
              <p className="truncate text-sm font-black">MSI School</p>
              <p className="truncate text-xs text-muted-foreground">{authLogin || "Teacher"}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <a
              href={routes.accountSecurity}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-background px-3 text-xs font-black text-foreground hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
            >
              <KeyRound className="h-3.5 w-3.5" />
              Password
            </a>
            <form action={routes.logout} method="post">
              <input type="hidden" name="csrf_token" value={csrfToken} />
              <button
                type="submit"
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-background px-3 text-xs font-black text-foreground hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
              >
                <LogOut className="h-3.5 w-3.5" />
                Logout
              </button>
            </form>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-5xl px-4 py-5 sm:px-6">
        {academyTeacher ? (
          <AcademyTeacherPreview teacher={academyTeacher} />
        ) : (
          <div className="rounded-2xl border border-border bg-surface p-8 text-center shadow-card">
            <p className="text-sm font-black text-foreground">Your Academy profile isn't available yet.</p>
            <p className="mt-1 text-xs font-semibold text-muted-foreground">
              Please contact your Academic Director. You can still change your password above.
            </p>
          </div>
        )}
      </section>
    </main>
  );
}
