import { ContactRound, CreditCard, GraduationCap, LayoutDashboard, TicketCheck, UsersRound } from "lucide-react";
import type { SupportWorkspaceView } from "@/features/customer-support/model";
import { ParentsPage } from "@/features/customer-support/parents/ParentsPage";
import { DashboardPlaceholder } from "@/features/customer-support/placeholders/DashboardPlaceholder";
import { PaymentsPlaceholder } from "@/features/customer-support/placeholders/PaymentsPlaceholder";
import { StudentsPage } from "@/features/customer-support/students/StudentsPage";
import { TeachersPage } from "@/features/customer-support/teachers/TeachersPage";
import { TicketsPage } from "@/features/customer-support/tickets/TicketsPage";
import { RoleWorkspaceShell } from "@/shared/ui/RoleWorkspaceShell";

type Props = {
  authLogin?: string;
  csrfToken?: string;
  title?: string;
  description?: string;
  view?: string;
};

const VALID_VIEWS = new Set<SupportWorkspaceView>(["dashboard", "payments", "parents", "students", "teachers", "tickets"]);
const CUSTOMER_SUPPORT_NAV_ITEMS = [
  { key: "dashboard", label: "Dashboard", href: "/customer-support/dashboard", icon: LayoutDashboard },
  { key: "payments", label: "Payments", href: "/customer-support/payments", icon: CreditCard },
  { key: "parents", label: "Parents", href: "/customer-support/parents", icon: UsersRound },
  { key: "students", label: "Students", href: "/customer-support/students", icon: GraduationCap },
  { key: "teachers", label: "Teachers", href: "/customer-support/teachers", icon: ContactRound },
  { key: "tickets", label: "Tickets", href: "/customer-support/tickets", icon: TicketCheck },
] as const;

function normalizeView(view: string | undefined): SupportWorkspaceView {
  return VALID_VIEWS.has(view as SupportWorkspaceView) ? view as SupportWorkspaceView : "dashboard";
}

export default function CustomerSupportWorkspace({
  authLogin = "",
  csrfToken = "",
  title = "Customer Support Dashboard",
  description = "Monitor Customer Support operations.",
  view,
}: Props) {
  const activeView = normalizeView(view);
  const pageProps = { authLogin, title, description };

  return (
    <RoleWorkspaceShell
      authLogin={authLogin}
      csrfToken={csrfToken}
      active={activeView}
      homeHref="/customer-support/dashboard"
      navItems={CUSTOMER_SUPPORT_NAV_ITEMS}
      roleLabel="Customer Support"
      sectionLabel="Customer Support"
      workspaceLabel="Customer Support"
      mobileNavigationMode="drawer"
      desktopSidebarMode="collapsible"
      maxWidthClass="max-w-[var(--workspace-content-max-width)]"
      sectionClassName="gap-0"
    >
      {activeView === "parents" ? (
        <ParentsPage key="parents" {...pageProps} csrfToken={csrfToken} />
      ) : activeView === "students" ? (
        <StudentsPage key="students" {...pageProps} csrfToken={csrfToken} />
      ) : activeView === "payments" ? (
        <PaymentsPlaceholder key="payments" {...pageProps} />
      ) : activeView === "teachers" ? (
        <TeachersPage key="teachers" {...pageProps} />
      ) : activeView === "tickets" ? (
        <TicketsPage key="tickets" {...pageProps} csrfToken={csrfToken} />
      ) : (
        <DashboardPlaceholder key="dashboard" {...pageProps} />
      )}
    </RoleWorkspaceShell>
  );
}
