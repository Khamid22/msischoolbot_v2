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
      className={`fixed inset-x-0 bottom-0 ${uiLayers.mobileNav} border-t border-border bg-surface/95 px-2 pt-2 shadow-card backdrop-blur lg:hidden`}
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
              className={`flex min-h-12 flex-col items-center justify-center gap-1 rounded-lg px-1 py-1 text-center text-[10.5px] font-bold leading-tight transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 motion-reduce:transition-none ${
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="max-w-full break-words">{item.label}</span>
            </a>
          );
        })}
      </div>
    </nav>
  );
}
