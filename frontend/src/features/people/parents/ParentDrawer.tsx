import { type ReactNode } from "react";
import {
  AtSign,
  ExternalLink,
  KeyRound,
  Link2,
  Link2Off,
  Mail,
  Phone,
  Power,
  Ticket,
} from "lucide-react";
import { Drawer } from "@/shared/ui/Drawer";
import { Badge } from "@/shared/ui/Badge";
import { routes } from "@/shared/lib/routes";
import {
  type ParentRow,
  childGroupLabel,
  isDisabled,
  openTicketCount,
  parentChildren,
  parentDisplayName,
  parentInitials,
  parentLogin,
  parentPhone,
  parentTelegram,
  shouldShowLogin,
  telegramConnected,
} from "./types";
import { type ParentHandlers, ParentStatusBadges } from "./actions";
import { asString, getStudentRowId } from "@/shared/lib/workspace";

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-2 rounded-lg border border-foreground/8 bg-background p-2.5">
      <h3 className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">{title}</h3>
      {children}
    </section>
  );
}

function InfoRow({ icon, label, value }: { icon: ReactNode; label: string; value: ReactNode }) {
  return (
    <div className="flex min-h-[3.8rem] items-start gap-2 rounded-lg border border-foreground/8 bg-muted/30 px-2.5 py-2">
      <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center text-muted-foreground">{icon}</span>
      <div className="min-w-0">
        <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">{label}</p>
        <div className="mt-0.5 break-words text-sm font-bold leading-5 text-foreground">{value}</div>
      </div>
    </div>
  );
}

function ticketRows(parent: ParentRow): ParentRow[] {
  for (const value of [parent.support_tickets, parent.tickets, parent.complaints]) {
    if (Array.isArray(value)) return value as ParentRow[];
  }
  return [];
}

function ActionButton({
  icon,
  label,
  onClick,
  disabled,
  tooltip,
  danger,
}: {
  icon: ReactNode;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  tooltip?: string;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={tooltip}
      className={`inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg border px-3 text-xs font-bold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-foreground/30 disabled:cursor-not-allowed disabled:opacity-50 sm:flex-1 ${
        danger
          ? "border-destructive/20 bg-destructive/10 text-destructive hover:bg-destructive/15"
          : "border-foreground/10 bg-background text-foreground hover:bg-muted"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

export function ParentDrawer({
  parent,
  handlers,
  onClose,
  currentSchool = "all",
}: {
  parent: ParentRow | null;
  handlers: ParentHandlers;
  onClose: () => void;
  currentSchool?: string;
}) {
  if (!parent) {
    return <Drawer open={false} onClose={onClose} title="" children={null} />;
  }

  const disabled = isDisabled(parent);
  const name = parentDisplayName(parent);
  const phone = parentPhone(parent);
  const telegram = parentTelegram(parent);
  const connected = telegramConnected(parent);
  const email = asString(parent.email);
  const children = parentChildren(parent);
  const visibleChildren = children.slice(0, 3);
  const extraChildren = Math.max(0, children.length - visibleChildren.length);
  const tickets = openTicketCount(parent);
  const visibleTickets = ticketRows(parent).slice(0, 3);
  const createdAt = asString(parent.created_at);

  return (
    <Drawer
      open
      onClose={onClose}
      title={
        <span className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted text-xs font-bold">
            {parentInitials(name)}
          </span>
          <span className="truncate">{name}</span>
        </span>
      }
      description={shouldShowLogin(parent) ? `Login: ${parentLogin(parent)}` : "Registered from student link"}
      headerExtra={<div className="hidden sm:block"><ParentStatusBadges parent={parent} /></div>}
      widthClass="sm:max-w-xl lg:max-w-2xl"
      footer={
        <div className="flex flex-col gap-2 sm:flex-row">
          <ActionButton icon={<Link2 className="h-3.5 w-3.5" />} label="Link student" onClick={() => handlers.onLinkStudent(parent)} />
          <ActionButton icon={<Ticket className="h-3.5 w-3.5" />} label="Open support" onClick={() => handlers.onOpenTickets(parent)} />
        </div>
      }
    >
      <div className="space-y-3">
        <div className="rounded-lg border border-foreground/8 bg-muted/30 p-3 sm:hidden">
          <ParentStatusBadges parent={parent} />
        </div>

        <Section title="Account">
          <div className="grid gap-2 sm:grid-cols-3">
            <InfoRow icon={<KeyRound className="h-4 w-4" />} label="Login" value={parentLogin(parent) || "—"} />
            <InfoRow
              icon={<Power className="h-4 w-4" />}
              label="Status"
              value={disabled ? "Disabled" : "Registered from student link"}
            />
            {createdAt ? (
              <InfoRow icon={<Ticket className="h-4 w-4" />} label="Added" value={createdAt.slice(0, 10)} />
            ) : null}
          </div>
        </Section>

        <Section title="Contact">
          <div className="grid gap-2 sm:grid-cols-3">
            <InfoRow
              icon={<Phone className="h-4 w-4" />}
              label="Phone"
              value={phone || <span className="font-semibold text-amber-700">Missing phone</span>}
            />
            <InfoRow icon={<Mail className="h-4 w-4" />} label="Email" value={email || "—"} />
            <InfoRow
              icon={<AtSign className="h-4 w-4" />}
              label="Telegram"
              value={
                <span className="flex flex-wrap items-center gap-1.5">
                  {telegram || "—"}
                  {connected ? <Badge tone="info">Connected</Badge> : <Badge tone="neutral">Not connected</Badge>}
                </span>
              }
            />
          </div>
        </Section>

        <Section title={`Linked students (${children.length})`}>
          {children.length ? (
            <div className="space-y-2">
              {visibleChildren.map((child, index) => {
                const studentRowId = getStudentRowId(child);
                const studentName = asString(child.full_name) || asString(child.student_id) || "Student";
                const href = studentRowId ? routes.adminStudentPanel(studentRowId, currentSchool) : "";
                return (
                  <div
                    key={asString(child.student_row_id) || asString(child.student_id) || index}
                    className="flex items-center justify-between gap-3 rounded-lg border border-foreground/8 bg-muted/30 px-3 py-2"
                  >
                    <a
                      href={href || undefined}
                      aria-disabled={!href}
                      className="flex min-w-0 flex-1 items-center gap-2.5 rounded-md outline-none hover:text-info focus-visible:ring-2 focus-visible:ring-foreground/30"
                    >
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-background text-xs font-bold shadow-sm">
                        {parentInitials(studentName)}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="flex min-w-0 items-center gap-1.5 text-sm font-bold text-foreground">
                          <span className="truncate">{studentName}</span>
                          {href ? <ExternalLink className="h-3 w-3 shrink-0 text-muted-foreground" /> : null}
                        </span>
                        <span className="block truncate text-xs text-muted-foreground">
                          {asString(child.student_id) ? `Code ${asString(child.student_id)}` : ""}
                          {childGroupLabel(child) ? ` · ${childGroupLabel(child)}` : ""}
                        </span>
                      </span>
                    </a>
                    <button
                      type="button"
                      onClick={() => handlers.onUnlinkChild(parent, child)}
                      className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-lg border border-foreground/10 bg-background px-2.5 text-xs font-bold text-muted-foreground hover:bg-muted hover:text-foreground"
                    >
                      <Link2Off className="h-3.5 w-3.5" />
                      Unlink
                    </button>
                  </div>
                );
              })}
              {extraChildren > 0 ? (
                <p className="px-1 text-xs font-semibold text-muted-foreground">
                  +{extraChildren} more linked {extraChildren === 1 ? "student" : "students"}
                </p>
              ) : null}
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-amber-200 bg-amber-50 px-3 py-5 text-center">
              <p className="text-sm font-bold text-amber-800">No linked students</p>
              <p className="mt-0.5 text-xs text-amber-700">Link a student so this parent can follow their progress.</p>
            </div>
          )}
        </Section>

        <Section title="Support tickets">
          <div className="space-y-2">
            {visibleTickets.length ? (
              visibleTickets.map((ticket, index) => (
                <button
                  key={asString(ticket.id) || index}
                  type="button"
                  onClick={() => handlers.onOpenTickets(parent)}
                  className="flex w-full items-center justify-between gap-3 rounded-lg border border-foreground/8 bg-muted/30 px-3 py-2 text-left hover:bg-muted"
                >
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-bold">
                      {asString(ticket.topic) || asString(ticket.category) || "Support ticket"}
                    </span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {asString(ticket.status) || "Open"}
                    </span>
                  </span>
                  <Ticket className="h-4 w-4 shrink-0 text-muted-foreground" />
                </button>
              ))
            ) : (
              <div className="flex items-center justify-between gap-2 rounded-lg border border-foreground/8 bg-muted/30 px-3 py-2.5">
                <div className="flex items-center gap-2 text-sm">
                  <Ticket className="h-4 w-4 text-muted-foreground" />
                  {tickets > 0 ? (
                    <span className="font-bold text-amber-700">
                      {tickets} open {tickets === 1 ? "ticket" : "tickets"}
                    </span>
                  ) : (
                    <span className="text-muted-foreground">No open tickets</span>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => handlers.onOpenTickets(parent)}
                  className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-foreground/10 bg-background px-2.5 text-xs font-bold hover:bg-muted"
                >
                  Open support
                </button>
              </div>
            )}
            {visibleTickets.length ? (
              <button
                type="button"
                onClick={() => handlers.onOpenTickets(parent)}
                className="inline-flex h-8 w-full items-center justify-center rounded-lg border border-foreground/10 bg-background px-2.5 text-xs font-bold hover:bg-muted"
              >
                Open support
              </button>
            ) : null}
          </div>
        </Section>
      </div>
    </Drawer>
  );
}
