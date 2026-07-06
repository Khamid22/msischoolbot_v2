import { useEffect, useId, useMemo, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { MoreVertical } from "lucide-react";
import { useDismissibleLayer } from "@/shared/lib/useDismissibleLayer";

export type ActionMenuItem =
  | { separator: true; key: string }
  | {
      key: string;
      label: string;
      icon?: ReactNode;
      onClick: () => void;
      disabled?: boolean;
      /** Shown as a native tooltip; useful to explain a disabled action. */
      tooltip?: string;
      danger?: boolean;
    };

interface ActionMenuProps {
  items: ActionMenuItem[];
  /** Accessible label for the trigger button. */
  label?: string;
  trigger?: ReactNode;
  align?: "left" | "right";
}

function isAction(item: ActionMenuItem): item is Extract<ActionMenuItem, { onClick: () => void }> {
  return !("separator" in item);
}

/**
 * Accessible three-dot dropdown menu. Keyboard operable (arrow keys, Enter,
 * Escape), closes on outside click, and returns focus to the trigger. Built to
 * be reused by any admin table row.
 */
export function ActionMenu({ items, label = "More actions", trigger, align = "right" }: ActionMenuProps) {
  const [open, setOpen] = useState(false);
  const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const menuId = useId();
  const dismissibleRefs = useMemo(() => [containerRef, menuRef], []);

  const actionIndexes = items
    .map((item, index) => (isAction(item) && !item.disabled ? index : -1))
    .filter((index) => index >= 0);

  function close(returnFocus = true) {
    setOpen(false);
    if (returnFocus) triggerRef.current?.focus();
  }

  function focusItem(index: number) {
    itemRefs.current[index]?.focus();
  }

  function updateMenuPosition() {
    const triggerRect = triggerRef.current?.getBoundingClientRect();
    if (!triggerRect) return;

    const menuWidth = 208;
    const gutter = 8;
    const preferredLeft = align === "right" ? triggerRect.right - menuWidth : triggerRect.left;
    const maxLeft = Math.max(gutter, window.innerWidth - menuWidth - gutter);

    setMenuPosition({
      top: triggerRect.bottom + 6,
      left: Math.min(Math.max(gutter, preferredLeft), maxLeft),
    });
  }

  useEffect(() => {
    if (!open) return;

    updateMenuPosition();
    window.addEventListener("resize", updateMenuPosition);
    window.addEventListener("scroll", updateMenuPosition, true);

    // Focus the first enabled item when the menu opens.
    const timer = window.setTimeout(() => {
      if (actionIndexes.length) focusItem(actionIndexes[0]);
    }, 0);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("resize", updateMenuPosition);
      window.removeEventListener("scroll", updateMenuPosition, true);
    };
  }, [open]);

  useDismissibleLayer({
    enabled: open,
    refs: dismissibleRefs,
    onDismiss: (event) => close(event.type === "keydown"),
  });

  function moveFocus(currentIndex: number, direction: 1 | -1) {
    if (!actionIndexes.length) return;
    const position = actionIndexes.indexOf(currentIndex);
    const nextPosition =
      position < 0
        ? direction === 1
          ? 0
          : actionIndexes.length - 1
        : (position + direction + actionIndexes.length) % actionIndexes.length;
    focusItem(actionIndexes[nextPosition]);
  }

  return (
    <div ref={containerRef} className="relative inline-block text-left">
      <button
        ref={triggerRef}
        type="button"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        onClick={(event) => {
          event.stopPropagation();
          if (!open) updateMenuPosition();
          setOpen((value) => !value);
        }}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" || event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            setOpen(true);
          }
        }}
        className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-foreground/30"
      >
        {trigger ?? <MoreVertical className="h-4 w-4" />}
      </button>

      {open && typeof document !== "undefined" ? createPortal(
        <div
          ref={menuRef}
          id={menuId}
          role="menu"
          aria-label={label}
          style={{ top: menuPosition.top, left: menuPosition.left }}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              event.preventDefault();
              close();
            }
          }}
          className={`fixed z-[90] w-52 overflow-hidden rounded-lg border border-foreground/10 bg-surface py-1 shadow-card-hover animate-in fade-in zoom-in-95 slide-in-from-top-1 duration-100 motion-reduce:animate-none ${
            align === "right" ? "origin-top-right" : "origin-top-left"
          }`}
        >
          {items.map((item, index) => {
            if (!isAction(item)) {
              return <div key={item.key} role="separator" className="my-1 h-px bg-foreground/8" />;
            }
            return (
              <button
                key={item.key}
                ref={(node) => {
                  itemRefs.current[index] = node;
                }}
                type="button"
                role="menuitem"
                disabled={item.disabled}
                title={item.tooltip}
                onClick={(event) => {
                  event.stopPropagation();
                  if (item.disabled) return;
                  close(false);
                  item.onClick();
                }}
                onKeyDown={(event) => {
                  if (event.key === "ArrowDown") {
                    event.preventDefault();
                    moveFocus(index, 1);
                  } else if (event.key === "ArrowUp") {
                    event.preventDefault();
                    moveFocus(index, -1);
                  }
                }}
                className={`flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm font-medium transition-colors focus:outline-none ${
                  item.disabled
                    ? "cursor-not-allowed text-muted-foreground/50"
                    : item.danger
                      ? "text-destructive hover:bg-destructive/10 focus-visible:bg-destructive/10"
                      : "text-foreground hover:bg-muted focus-visible:bg-muted"
                }`}
              >
                {item.icon ? <span className="flex h-4 w-4 shrink-0 items-center justify-center">{item.icon}</span> : null}
                <span className="truncate">{item.label}</span>
              </button>
            );
          })}
        </div>,
        document.body,
      ) : null}
    </div>
  );
}
