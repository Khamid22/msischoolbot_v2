import { BookOpen, CreditCard, LifeBuoy, LogOut } from "lucide-react";
import type { ReactNode } from "react";
import type { BillingAccessStatus } from "@/shared/billing/model";

type StudentAccountView = "payments" | "support";

const ACCOUNT_NAV = [
  { key: "payments", label: "To‘lovlar", href: "/student/payments", icon: CreditCard },
  { key: "support", label: "Yordam", href: "/student/support", icon: LifeBuoy },
] as const;

export function StudentAccountShell({
  active,
  status,
  authLogin = "",
  csrfToken = "",
  logoutUrl = "/logout",
  children,
}: {
  active: StudentAccountView;
  status?: BillingAccessStatus;
  authLogin?: string;
  csrfToken?: string;
  logoutUrl?: string;
  children: ReactNode;
}) {
  const isPaymentOnly = status?.mode === "payment_only";
  return (
    <div className="min-h-[var(--tg-viewport-height)] bg-background text-foreground">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 border-r border-sidebar-border bg-sidebar px-3 py-4 text-sidebar-foreground lg:flex lg:flex-col">
        <a href="/student" className="flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm font-black text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-white/10">M</span>
          MSI School
        </a>
        <p className="mt-5 px-3 text-[0.6875rem] font-bold uppercase tracking-wider text-slate-400">
          Student
        </p>
        <nav className="mt-2 space-y-1" aria-label="Student account navigation">
          {!isPaymentOnly ? (
            <a href="/student" className="flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm font-semibold text-slate-300 hover:bg-white/10 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50">
              <BookOpen className="h-5 w-5" aria-hidden="true" />
              O‘qish
            </a>
          ) : null}
          {ACCOUNT_NAV.map((item) => {
            const Icon = item.icon;
            const isActive = active === item.key;
            return (
              <a
                key={item.key}
                href={item.href}
                aria-current={isActive ? "page" : undefined}
                className={`flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50 ${
                  isActive
                    ? "bg-sidebar-primary text-sidebar-primary-foreground"
                    : "text-slate-300 hover:bg-white/10 hover:text-white"
                }`}
              >
                <Icon className="h-5 w-5" aria-hidden="true" />
                {item.label}
              </a>
            );
          })}
        </nav>
        <form action={logoutUrl} method="post" className="mt-auto">
          <input type="hidden" name="csrf_token" value={csrfToken} />
          <button type="submit" className="flex min-h-11 w-full items-center gap-3 rounded-lg px-3 text-sm font-semibold text-slate-300 hover:bg-white/10 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50">
            <LogOut className="h-5 w-5" aria-hidden="true" />
            Chiqish
          </button>
        </form>
      </aside>

      <main className="min-h-[var(--tg-viewport-height)] px-3 pb-[calc(var(--app-bottom-inset)+6rem)] pt-[calc(var(--app-top-inset)+0.75rem)] sm:px-5 lg:ml-64 lg:pb-8 lg:pt-6">
        <div className="mx-auto flex w-full max-w-5xl flex-col gap-4">
          <header className="flex items-center justify-between rounded-xl border border-border bg-surface px-4 py-3 shadow-card lg:hidden">
            <div>
              <p className="text-xs font-bold text-muted-foreground">MSI Student</p>
              <p className="text-sm font-black">{authLogin || "Student"}</p>
            </div>
            <form action={logoutUrl} method="post">
              <input type="hidden" name="csrf_token" value={csrfToken} />
              <button type="submit" aria-label="Chiqish" className="grid h-11 w-11 place-items-center rounded-lg border border-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                <LogOut className="h-5 w-5" aria-hidden="true" />
              </button>
            </form>
          </header>
          {children}
        </div>
      </main>

      <nav
        className="fixed inset-x-3 bottom-[calc(var(--app-bottom-inset)+0.75rem)] z-40 grid grid-cols-2 rounded-2xl border border-border bg-surface/95 p-1.5 shadow-xl backdrop-blur lg:hidden"
        aria-label="Student account navigation"
      >
        {ACCOUNT_NAV.map((item) => {
          const Icon = item.icon;
          const isActive = active === item.key;
          return (
            <a
              key={item.key}
              href={item.href}
              aria-current={isActive ? "page" : undefined}
              className={`flex min-h-12 items-center justify-center gap-2 rounded-xl px-3 text-xs font-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                isActive ? "bg-primary text-primary-foreground" : "text-muted-foreground"
              }`}
            >
              <Icon className="h-5 w-5" aria-hidden="true" />
              {item.label}
            </a>
          );
        })}
      </nav>
    </div>
  );
}
