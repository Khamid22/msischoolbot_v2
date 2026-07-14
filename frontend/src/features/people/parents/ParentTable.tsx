import { AtSign, Eye, Phone, Ticket } from "lucide-react";
import { Badge } from "@/shared/ui/Badge";
import { ActionMenu } from "@/shared/ui/ActionMenu";
import {
  type ParentRow,
  isInviteSource,
  openTicketCount,
  parentAccountId,
  parentChildren,
  parentDisplayName,
  parentInitials,
  parentLogin,
  parentPhone,
  parentTelegram,
  shouldShowLogin,
  telegramConnected,
} from "./types";
import { type ParentHandlers, ParentStatusBadges, buildParentMenuItems } from "./actions";
import { asString } from "@/shared/lib/workspace";

function ContactCell({ parent }: { parent: ParentRow }) {
  const phone = parentPhone(parent);
  const telegram = parentTelegram(parent);
  const connected = telegramConnected(parent);
  return (
    <div className="space-y-1">
      {phone ? (
        <span className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
          <Phone className="h-3.5 w-3.5 text-muted-foreground" />
          {phone}
        </span>
      ) : (
        <Badge tone="warning" icon={<Phone className="h-3 w-3" />}>
          Missing phone
        </Badge>
      )}
      <span className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
        <AtSign className="h-3.5 w-3.5" />
        {telegram ? <span className="truncate">{telegram}</span> : <span>No Telegram</span>}
        {connected ? <Badge tone="info">Connected</Badge> : null}
      </span>
    </div>
  );
}

function LinkedStudentsCell({ parent }: { parent: ParentRow }) {
  const kids = parentChildren(parent);
  if (!kids.length) {
    return <Badge tone="warning">Not linked</Badge>;
  }
  const shown = kids.slice(0, 3);
  const extra = kids.length - shown.length;
  return (
    <div className="flex max-w-xs flex-wrap gap-1">
      {shown.map((child, index) => (
        <span
          key={asString(child.student_row_id) || asString(child.student_id) || index}
          className="rounded-full bg-muted px-2 py-0.5 text-[11px] font-semibold text-foreground"
        >
          {asString(child.full_name) || asString(child.student_id) || "Student"}
        </span>
      ))}
      {extra > 0 ? (
        <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] font-semibold text-muted-foreground">
          +{extra}
        </span>
      ) : null}
    </div>
  );
}

function TicketsBadge({ parent, onOpen }: { parent: ParentRow; onOpen: () => void }) {
  const count = openTicketCount(parent);
  if (count <= 0) {
    return <span className="text-xs text-muted-foreground">0 open</span>;
  }
  return (
    <Badge tone="warning" icon={<Ticket className="h-3 w-3" />} onClick={onOpen} title="View support tickets">
      {count} open
    </Badge>
  );
}

function ParentIdentity({ parent, onView }: { parent: ParentRow; onView: () => void }) {
  const name = parentDisplayName(parent);
  return (
    <div className="flex min-w-0 items-center gap-3">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted text-xs font-bold text-foreground">
        {parentInitials(name)}
      </span>
      <span className="min-w-0">
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            onView();
          }}
          className="block max-w-full truncate text-left text-sm font-bold text-foreground hover:underline focus:outline-none focus-visible:underline"
        >
          {name}
        </button>
        <span className="mt-0.5 flex items-center gap-1.5">
          {shouldShowLogin(parent) ? (
            <span className="truncate text-xs text-muted-foreground">{parentLogin(parent)}</span>
          ) : null}
          {isInviteSource(parent) ? <Badge tone="info">Registered</Badge> : null}
        </span>
      </span>
    </div>
  );
}

function RowActions({ parent, handlers }: { parent: ParentRow; handlers: ParentHandlers }) {
  return (
    <div className="flex items-center justify-end gap-1">
      <button
        type="button"
        onClick={(event) => {
          event.stopPropagation();
          handlers.onView(parent);
        }}
        className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-foreground/10 bg-background px-2.5 text-xs font-bold hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-foreground/30"
      >
        <Eye className="h-3.5 w-3.5" />
        View
      </button>
      <ActionMenu label={`Actions for ${parentDisplayName(parent)}`} items={buildParentMenuItems(parent, handlers)} />
    </div>
  );
}

function parentKey(parent: ParentRow) {
  return String(parentAccountId(parent) || "") || asString(parent.id) || asString(parent.parent_id) || parentLogin(parent);
}

export function ParentTable({
  parents,
  handlers,
  className = "",
}: {
  parents: ParentRow[];
  handlers: ParentHandlers;
  className?: string;
}) {
  return (
    <div className={`flex min-h-0 flex-col ${className}`}>
      {/* Desktop / laptop table */}
      <div className="hidden min-h-0 flex-1 overflow-auto rounded-lg border border-foreground/10 bg-white md:block">
        <table className="w-full min-w-[820px] table-fixed text-left text-xs">
          <thead className="sticky top-0 z-10 bg-muted text-[10px] font-bold uppercase tracking-wider text-muted-foreground shadow-[0_1px_0_hsl(var(--foreground)/0.08)]">
            <tr>
              <th className="w-[22%] px-3 py-2">Parent</th>
              <th className="w-[20%] px-3 py-2">Contact</th>
              <th className="w-[24%] px-3 py-2">Linked students</th>
              <th className="w-[14%] px-3 py-2">Account status</th>
              <th className="w-[10%] px-3 py-2">Open tickets</th>
              <th className="w-[10%] px-3 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-foreground/5">
            {parents.map((parent) => (
              <tr
                key={parentKey(parent)}
                onClick={() => handlers.onView(parent)}
                className="cursor-pointer bg-white transition-colors hover:bg-muted/30"
              >
                <td className="px-3 py-3">
                  <ParentIdentity parent={parent} onView={() => handlers.onView(parent)} />
                </td>
                <td className="px-3 py-3">
                  <ContactCell parent={parent} />
                </td>
                <td className="px-3 py-3">
                  <LinkedStudentsCell parent={parent} />
                </td>
                <td className="px-3 py-3">
                  <ParentStatusBadges parent={parent} />
                </td>
                <td className="px-3 py-3">
                  <TicketsBadge parent={parent} onOpen={() => handlers.onOpenTickets(parent)} />
                </td>
                <td className="relative px-3 py-3" onClick={(event) => event.stopPropagation()}>
                  <RowActions parent={parent} handlers={handlers} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile cards */}
      <div className="space-y-2 md:hidden">
        {parents.map((parent) => (
          <div
            key={parentKey(parent)}
            onClick={() => handlers.onView(parent)}
            className="cursor-pointer rounded-lg border border-foreground/10 bg-white p-3 shadow-card"
          >
            <div className="flex items-start justify-between gap-2">
              <ParentIdentity parent={parent} onView={() => handlers.onView(parent)} />
              <div onClick={(event) => event.stopPropagation()}>
                <ActionMenu
                  label={`Actions for ${parentDisplayName(parent)}`}
                  items={buildParentMenuItems(parent, handlers)}
                />
              </div>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-1.5">
              <ParentStatusBadges parent={parent} />
              <TicketsBadge parent={parent} onOpen={() => handlers.onOpenTickets(parent)} />
            </div>
            <div className="mt-3 grid grid-cols-1 gap-2 border-t border-foreground/5 pt-3">
              <ContactCell parent={parent} />
              <div onClick={(event) => event.stopPropagation()}>
                <LinkedStudentsCell parent={parent} />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
