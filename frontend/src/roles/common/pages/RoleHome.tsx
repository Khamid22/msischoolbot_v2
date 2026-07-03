import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  LayoutDashboard,
  ShieldCheck,
} from "lucide-react";

interface RoleHomeCard {
  label?: string;
  value?: string;
  description?: string;
}

interface RoleHomeProps {
  authLogin?: string;
  roleDisplayName?: string;
  title?: string;
  description?: string;
  cards?: RoleHomeCard[];
}

function MetricCard({ label, value, description }: Required<RoleHomeCard>) {
  return (
    <section className="rounded-xl border border-border bg-surface px-4 py-3 shadow-sm">
      <p className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="mt-2 text-2xl font-black leading-none text-foreground">{value}</p>
      {description ? (
        <p className="mt-2 text-xs leading-5 text-muted-foreground">{description}</p>
      ) : null}
    </section>
  );
}

export function RoleHome({
  authLogin = "",
  roleDisplayName = "Workspace",
  title = "Workspace Dashboard",
  description = "Your role workspace is ready.",
  cards = [],
}: RoleHomeProps) {
  const normalizedCards = cards.length
    ? cards
    : [
        { label: "Access", value: "Ready", description: "Your account role is active." },
        { label: "Routes", value: "Guarded", description: "Wrong workspaces are blocked." },
        { label: "Cabinet", value: "Live", description: "This page can grow into the full role UI." },
      ];

  return (
    <main className="min-h-[var(--tg-viewport-height)] bg-background px-4 py-5 text-foreground sm:px-6 lg:px-8">
      <section className="mx-auto flex max-w-6xl flex-col gap-5">
        <header className="rounded-2xl border border-border bg-surface p-5 shadow-card">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <LayoutDashboard className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
                  {roleDisplayName}
                </p>
                <h1 className="mt-1 text-2xl font-black tracking-normal text-foreground">
                  {title}
                </h1>
                <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">
                  {description}
                </p>
              </div>
            </div>
            {authLogin ? (
              <div className="inline-flex items-center gap-2 rounded-full border border-border bg-muted px-3 py-2 text-xs font-bold text-muted-foreground">
                <ShieldCheck className="h-4 w-4 text-emerald-600" />
                {authLogin}
              </div>
            ) : null}
          </div>
        </header>

        <div className="grid gap-3 md:grid-cols-3">
          {normalizedCards.map((card) => (
            <MetricCard
              key={`${card.label || "card"}-${card.value || "value"}`}
              label={card.label || "Status"}
              value={card.value || "Ready"}
              description={card.description || ""}
            />
          ))}
        </div>

        <section className="rounded-2xl border border-border bg-surface p-5 shadow-card">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700">
                <CheckCircle2 className="h-4 w-4" />
                Role routing connected
              </div>
              <h2 className="mt-4 text-lg font-black text-foreground">Foundation is stable</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                This workspace is backed by canonical server-side role guards. The detailed
                modules can now be expanded without falling back into another role.
              </p>
            </div>
            <div className="flex items-center gap-2 rounded-xl bg-muted px-4 py-3 text-sm font-bold text-foreground">
              <BarChart3 className="h-4 w-4 text-primary" />
              Next panels can mount here
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </div>
          </div>
        </section>
      </section>
    </main>
  );
}

export default RoleHome;
