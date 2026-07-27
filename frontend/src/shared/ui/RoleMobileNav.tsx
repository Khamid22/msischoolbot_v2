import { uiLayers } from "@/shared/ui/layers";
import type { RoleNavItem } from "@/shared/ui/roleNav";

export interface RoleMobileNavProps<Key extends string = string> {
  active: Key;
  items: ReadonlyArray<RoleNavItem<Key>>;
  label: string;
  variant?: "bar" | "floating";
  primaryKey?: Key;
}

/**
 * Fixed bottom navigation for phones/tablets, hidden at `lg` and up where the
 * sidebar takes over. Respects safe-area insets and never truncates labels —
 * pass short `mobileLabel`s (via mobileNavItemsFrom) instead of clipping.
 * Page content must reserve bottom padding; RoleWorkspaceShell does this.
 */
export function RoleMobileNav<Key extends string = string>({
  active,
  items,
  label,
  variant = "bar",
  primaryKey,
}: RoleMobileNavProps<Key>) {
  const isFloating = variant === "floating";
  return (
    <nav
      className={`fixed inset-x-0 bottom-0 ${uiLayers.mobileNav} px-2 pt-2 lg:hidden ${
        isFloating
          ? "pointer-events-none"
          : "border-t border-border/80 bg-card/95 shadow-card backdrop-blur"
      }`}
      style={{
        paddingBottom: "max(0.5rem, var(--app-bottom-inset))",
        paddingLeft: "calc(var(--app-left-inset) + 0.5rem)",
        paddingRight: "calc(var(--app-right-inset) + 0.5rem)",
      }}
      aria-label={label}
    >
      <div
        className={`mx-auto grid max-w-lg gap-1 ${
          isFloating
            ? "pointer-events-auto rounded-2xl border border-border/80 bg-card/95 px-1.5 py-1.5 shadow-xl backdrop-blur"
            : ""
        }`}
        style={{ gridTemplateColumns: `repeat(${items.length}, minmax(0, 1fr))` }}
      >
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = active === item.key;
          const isPrimary = isFloating && primaryKey === item.key;
          return (
            <a
              key={item.key}
              href={item.href}
              aria-current={isActive ? "page" : undefined}
              className={`relative flex min-h-[3.25rem] flex-col items-center justify-center gap-1 rounded-xl px-1 py-1 text-center text-[0.65625rem] font-black leading-[1.05] transition-[background-color,color,box-shadow,transform] duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 motion-reduce:transition-none ${
                isPrimary
                  ? "-translate-y-3 bg-transparent text-primary"
                  : isActive
                    ? isFloating
                      ? "bg-primary/10 text-primary"
                      : "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:bg-muted/80 hover:text-foreground"
              }`}
            >
              {isPrimary ? (
                <span
                  className="flex h-11 w-11 items-center justify-center rounded-full border-4 border-card bg-primary text-primary-foreground shadow-lg"
                  aria-hidden="true"
                >
                  <Icon className="h-5 w-5 shrink-0" />
                </span>
              ) : (
                <Icon className="h-[1.125rem] w-[1.125rem] shrink-0" />
              )}
              {item.badge ? <span className="absolute right-[18%] top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-amber-400 px-1 text-[0.5625rem] font-bold text-slate-950" aria-label={`${item.badge} unread`}>{item.badge > 99 ? "99+" : item.badge}</span> : null}
              <span className={`max-w-full break-words ${isPrimary ? "-mt-0.5" : ""}`}>
                {item.label}
              </span>
            </a>
          );
        })}
      </div>
    </nav>
  );
}
