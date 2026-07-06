import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  LayoutDashboard,
  ShieldCheck,
} from "lucide-react";
import {
  AcademicDirectorPageShell,
  AcademicDirectorProfileSection,
  AcademicDirectorTeacherAcademyCta,
  HeadOfDepartmentPageShell,
  HeadOfDepartmentProfileSection,
  HeadOfDepartmentTeacherAcademyCta,
  academicDirectorActiveNavFromPath,
  headOfDepartmentActiveNavFromPath,
  type AcademicDirectorNavKey,
  type HeadOfDepartmentNavKey,
} from "@/roles/common/components/AcademicDirectorShell";

interface RoleHomeCard {
  label?: string;
  value?: string;
  description?: string;
  detail?: string;
}

interface RoleHomeProps {
  authLogin?: string;
  authRole?: string;
  role?: string;
  roleDisplayName?: string;
  title?: string;
  description?: string;
  cards?: RoleHomeCard[];
  csrfToken?: string;
}

function MetricCard({ label, value, description, detail }: Required<RoleHomeCard>) {
  const supportingText = description || detail;
  return (
    <section className="rounded-xl border border-border bg-surface px-4 py-3 shadow-sm">
      <p className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="mt-2 text-2xl font-black leading-none text-foreground">{value}</p>
      {supportingText ? (
        <p className="mt-2 text-xs leading-5 text-muted-foreground">{supportingText}</p>
      ) : null}
    </section>
  );
}

function normalizeRoleName(value: string | undefined) {
  return String(value || "").trim().toLowerCase().replace(/-/g, "_");
}

function currentAcademicDirectorNav(): AcademicDirectorNavKey {
  if (typeof window === "undefined") return "overview";
  return academicDirectorActiveNavFromPath(window.location.pathname, window.location.hash);
}

function currentHeadOfDepartmentNav(): HeadOfDepartmentNavKey {
  if (typeof window === "undefined") return "overview";
  return headOfDepartmentActiveNavFromPath(window.location.pathname, window.location.hash);
}

function AcademicDirectorHome({
  authLogin,
  roleDisplayName,
  title,
  description,
  cards,
  csrfToken,
}: Required<Pick<RoleHomeProps, "roleDisplayName" | "title" | "description" | "cards">> &
  Pick<RoleHomeProps, "authLogin" | "csrfToken">) {
  const activeNav = currentAcademicDirectorNav();
  const normalizedCards = cards.length
    ? cards
    : [
        { label: "Groups", value: "Ready", description: "Academic groups are available." },
        { label: "Teachers", value: "Ready", description: "Teacher records are available." },
        { label: "Subjects", value: "Ready", description: "Subject records are available." },
        { label: "Students", value: "Ready", description: "Student records are available." },
      ];

  return (
    <AcademicDirectorPageShell
      authLogin={authLogin}
      csrfToken={csrfToken}
      active={activeNav}
      maxWidthClass="max-w-6xl"
    >
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
                  <h1 className="mt-1 break-words text-2xl font-black tracking-normal text-foreground">
                    {title}
                  </h1>
                  <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">
                    {description}
                  </p>
                </div>
              </div>
              {authLogin ? (
                <div className="inline-flex max-w-full items-center gap-2 rounded-full border border-border bg-muted px-3 py-2 text-xs font-bold text-muted-foreground">
                  <ShieldCheck className="h-4 w-4 text-emerald-600" />
                  <span className="truncate">{authLogin}</span>
                </div>
              ) : null}
            </div>
          </header>

          <div className="grid gap-2 sm:grid-cols-2 sm:gap-3 lg:grid-cols-4">
            {normalizedCards.map((card) => (
              <MetricCard
                key={`${card.label || "card"}-${card.value || "value"}`}
                label={card.label || "Status"}
                value={card.value || "Ready"}
                description={card.description || ""}
                detail={card.detail || ""}
              />
            ))}
          </div>

          <AcademicDirectorTeacherAcademyCta />
          <AcademicDirectorProfileSection authLogin={authLogin} csrfToken={csrfToken} />
    </AcademicDirectorPageShell>
  );
}

function HeadOfDepartmentHome({
  authLogin,
  roleDisplayName,
  title,
  description,
  cards,
  csrfToken,
}: Required<Pick<RoleHomeProps, "roleDisplayName" | "title" | "description" | "cards">> &
  Pick<RoleHomeProps, "authLogin" | "csrfToken">) {
  const activeNav = currentHeadOfDepartmentNav();
  const normalizedCards = cards.length
    ? cards
    : [
        { label: "Subject Scope", value: "Ready", description: "Assigned subjects are available." },
        { label: "Teacher Academy", value: "Ready", description: "Academy teachers are subject-scoped." },
        { label: "Reports", value: "Ready", description: "Assessment reports are available." },
      ];

  return (
    <HeadOfDepartmentPageShell
      authLogin={authLogin}
      csrfToken={csrfToken}
      active={activeNav}
      maxWidthClass="max-w-6xl"
    >
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
                  <h1 className="mt-1 break-words text-2xl font-black tracking-normal text-foreground">
                    {title}
                  </h1>
                  <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">
                    {description}
                  </p>
                </div>
              </div>
              {authLogin ? (
                <div className="inline-flex max-w-full items-center gap-2 rounded-full border border-border bg-muted px-3 py-2 text-xs font-bold text-muted-foreground">
                  <ShieldCheck className="h-4 w-4 text-emerald-600" />
                  <span className="truncate">{authLogin}</span>
                </div>
              ) : null}
            </div>
          </header>

          <div className="grid gap-2 sm:grid-cols-2 sm:gap-3 lg:grid-cols-4">
            {normalizedCards.map((card) => (
              <MetricCard
                key={`${card.label || "card"}-${card.value || "value"}`}
                label={card.label || "Status"}
                value={card.value || "Ready"}
                description={card.description || ""}
                detail={card.detail || ""}
              />
            ))}
          </div>

          <HeadOfDepartmentTeacherAcademyCta />
          <HeadOfDepartmentProfileSection authLogin={authLogin} csrfToken={csrfToken} />
    </HeadOfDepartmentPageShell>
  );
}

export function RoleHome({
  authLogin = "",
  authRole = "",
  role = "",
  roleDisplayName = "Workspace",
  title = "Workspace Dashboard",
  description = "Your role workspace is ready.",
  cards = [],
  csrfToken = "",
}: RoleHomeProps) {
  const normalizedRole = normalizeRoleName(role || authRole);
  if (normalizedRole === "academic_director") {
    return (
      <AcademicDirectorHome
        authLogin={authLogin}
        roleDisplayName={roleDisplayName}
        title={title}
        description={description}
        cards={cards}
        csrfToken={csrfToken}
      />
    );
  }
  if (normalizedRole === "head_of_department") {
    return (
      <HeadOfDepartmentHome
        authLogin={authLogin}
        roleDisplayName={roleDisplayName}
        title={title}
        description={description}
        cards={cards}
        csrfToken={csrfToken}
      />
    );
  }

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
              detail={card.detail || ""}
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
