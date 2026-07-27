import {
  Bell,
  CreditCard,
  Home,
  LifeBuoy,
  LogOut,
  UserRound,
  UsersRound,
} from "lucide-react";
import type { FormEvent, ReactNode } from "react";
import { csrfHeaders } from "@/shared/lib/api";
import { RoleWorkspaceShell } from "@/shared/ui/RoleWorkspaceShell";
import type { RoleNavItem } from "@/shared/ui/roleNav";
import { ChildSelector } from "@/workspaces/parent/components";
import { parentCopy } from "@/workspaces/parent/copy";
import type {
  ParentChild,
  ParentLanguage,
  ParentNavKey,
} from "@/workspaces/parent/model";

function parentNavigation(language: ParentLanguage): ReadonlyArray<RoleNavItem<ParentNavKey>> {
  const copy = parentCopy[language];
  return [
    { key: "home", label: copy.home, href: "/parent", icon: Home },
    { key: "updates", label: copy.updates, href: "/parent/updates", icon: Bell },
    { key: "children", label: copy.children, href: "/parent/children", icon: UsersRound },
    { key: "payments", label: copy.payments, href: "/parent/payments", icon: CreditCard },
    { key: "support", label: copy.support, href: "/parent/support", icon: LifeBuoy },
  ];
}

function ParentTopbar({
  authLogin,
  csrfToken,
  logoutUrl,
  language,
  onLanguageChange,
  children,
  selectedStudentId,
  onChildChange,
}: {
  authLogin: string;
  csrfToken: string;
  logoutUrl: string;
  language: ParentLanguage;
  onLanguageChange: (language: ParentLanguage) => void;
  children: ParentChild[];
  selectedStudentId: number | null;
  onChildChange: (studentId: number | null) => void;
}) {
  const copy = parentCopy[language];

  async function logout(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await fetch(logoutUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: csrfHeaders(csrfToken),
    }).catch(() => undefined);
    window.location.assign("/?logged_out=1");
  }

  return (
    <div className="sticky top-[calc(var(--app-top-inset)+0.5rem)] z-30 flex items-center gap-2 rounded-xl border border-border/80 bg-card/95 p-2 shadow-card backdrop-blur">
      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
        <UserRound className="h-5 w-5" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-black text-foreground">{authLogin || copy.role}</p>
        <p className="truncate text-xs text-muted-foreground">{copy.role}</p>
      </div>
      {children.length ? (
        <div className="hidden min-w-0 sm:block">
          <ChildSelector
            children={children}
            selectedId={selectedStudentId}
            language={language}
            onChange={onChildChange}
          />
        </div>
      ) : null}
      <details className="group relative">
        <summary className="flex h-11 w-11 cursor-pointer list-none items-center justify-center rounded-lg border border-border bg-background text-foreground transition-colors hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 [&::-webkit-details-marker]:hidden">
          <UserRound className="h-4 w-4" />
          <span className="sr-only">{copy.language}</span>
        </summary>
        <div className="absolute right-0 top-[calc(100%+0.5rem)] w-52 rounded-xl border border-border bg-card p-2 shadow-xl">
          <p className="px-2 py-1 text-xs font-bold text-muted-foreground">{copy.language}</p>
          <div className="grid grid-cols-2 gap-1">
            {(["ru", "uz"] as const).map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => onLanguageChange(item)}
                aria-pressed={language === item}
                className={`min-h-11 rounded-lg px-3 text-sm font-bold focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 ${
                  language === item
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-foreground hover:bg-muted/70"
                }`}
              >
                {item.toUpperCase()}
              </button>
            ))}
          </div>
          <form onSubmit={logout} className="mt-2 border-t border-border pt-2">
            <button
              type="submit"
              className="flex min-h-11 w-full items-center gap-2 rounded-lg px-3 text-sm font-bold text-destructive hover:bg-destructive/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-destructive/35"
            >
              <LogOut className="h-4 w-4" />
              {copy.logout}
            </button>
          </form>
        </div>
      </details>
    </div>
  );
}

export function ParentWorkspaceShell({
  authLogin,
  csrfToken,
  logoutUrl,
  active,
  language,
  onLanguageChange,
  childrenList,
  selectedStudentId,
  onChildChange,
  children,
}: {
  authLogin: string;
  csrfToken: string;
  logoutUrl: string;
  active: ParentNavKey;
  language: ParentLanguage;
  onLanguageChange: (language: ParentLanguage) => void;
  childrenList: ParentChild[];
  selectedStudentId: number | null;
  onChildChange: (studentId: number | null) => void;
  children: ReactNode;
}) {
  const copy = parentCopy[language];
  const navItems = parentNavigation(language);
  return (
    <RoleWorkspaceShell
      authLogin={authLogin}
      csrfToken={csrfToken}
      active={active}
      homeHref="/parent"
      navItems={navItems}
      mobileNavItems={navItems}
      roleLabel={copy.role}
      sectionLabel={copy.section}
      workspaceLabel={copy.role}
      navLabel={`${copy.role} navigation`}
      mobileNavLabel={`${copy.role} mobile navigation`}
      initialsFallback="PR"
      profileHref="/parent"
      mobileNavigationMode="bottom"
      mobileNavVariant="floating"
      mobilePrimaryKey="children"
      maxWidthClass="max-w-[var(--workspace-content-max-width)]"
      sectionClassName="gap-4"
    >
      <ParentTopbar
        authLogin={authLogin}
        csrfToken={csrfToken}
        logoutUrl={logoutUrl}
        language={language}
        onLanguageChange={onLanguageChange}
        children={childrenList}
        selectedStudentId={selectedStudentId}
        onChildChange={onChildChange}
      />
      {childrenList.length ? (
        <div className="sm:hidden">
          <ChildSelector
            children={childrenList}
            selectedId={selectedStudentId}
            language={language}
            onChange={onChildChange}
          />
        </div>
      ) : null}
      {children}
    </RoleWorkspaceShell>
  );
}

export { parentNavigation };
