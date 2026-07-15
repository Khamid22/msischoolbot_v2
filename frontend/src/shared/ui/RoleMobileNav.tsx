import { uiLayers } from "@/shared/ui/layers";
import type { RoleNavItem } from "@/shared/ui/roleNav";

export interface RoleMobileNavProps<Key extends string = string> {
  active: Key;
  items: ReadonlyArray<RoleNavItem<Key>>;
  label: string;
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
}: RoleMobileNavProps<Key>) {
  return (
    <nav
      className={`fixed inset-x-0 bottom-0 ${uiLayers.mobileNav} border-t border-border/80 bg-card/95 px-2 pt-2 shadow-card backdrop-blur lg:hidden`}
      style={{
        paddingBottom: "max(0.5rem, var(--app-bottom-inset))",
        paddingLeft: "calc(var(--app-left-inset) + 0.5rem)",
        paddingRight: "calc(var(--app-right-inset) + 0.5rem)",
      }}
      aria-label={label}
    >
      <div
        className="mx-auto grid max-w-lg gap-1"
        style={{ gridTemplateColumns: `repeat(${items.length}, minmax(0, 1fr))` }}
      >
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = active === item.key;
          return (
            <a
              key={item.key}
              href={item.href}
              aria-current={isActive ? "page" : undefined}
              className={`relative flex min-h-[3.25rem] flex-col items-center justify-center gap-1 rounded-lg px-1 py-1 text-center text-[10.5px] font-black leading-[1.05] transition-[background-color,color,box-shadow] duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 motion-reduce:transition-none ${
                isActive
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:bg-muted/80 hover:text-foreground"
              }`}
            >
              <Icon className="h-[1.125rem] w-[1.125rem] shrink-0" />
              {item.badge ? <span className="absolute right-[18%] top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-amber-400 px-1 text-[9px] font-bold text-slate-950" aria-label={`${item.badge} unread`}>{item.badge > 99 ? "99+" : item.badge}</span> : null}
              <span className="max-w-full break-words">{item.label}</span>
            </a>
          );
        })}
      </div>
    </nav>
  );
}
