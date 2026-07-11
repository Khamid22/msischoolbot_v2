import { type ReactNode } from "react";
import { Link2, Link2Off, PhoneOff, Ticket, Users } from "lucide-react";
import {
  type ParentFilters,
  type ParentRow,
  isLinked,
  missingContact,
  openTicketCount,
} from "./types";

interface SummaryCard {
  key: string;
  label: string;
  value: number;
  icon: ReactNode;
  accent: string;
  active: boolean;
  onClick?: () => void;
}

export function ParentSummaryCards({
  parents,
  filters,
  onApply,
}: {
  parents: ParentRow[];
  filters: ParentFilters;
  onApply: (patch: Partial<ParentFilters>) => void;
}) {
  const total = parents.length;
  const linked = parents.filter(isLinked).length;
  const unlinked = total - linked;
  const missing = parents.filter(missingContact).length;
  const openTickets = parents.reduce((sum, parent) => sum + openTicketCount(parent), 0);

  const cards: SummaryCard[] = [
    {
      key: "total",
      label: "Total parents",
      value: total,
      icon: <Users className="h-4 w-4" />,
      accent: "text-foreground",
      active: false,
      onClick: () => onApply({ link: "all", contact: "all", account: "all", tickets: "all", groupClass: "all" }),
    },
    {
      key: "linked",
      label: "Linked",
      value: linked,
      icon: <Link2 className="h-4 w-4 text-emerald-600" />,
      accent: "text-emerald-700",
      active: filters.link === "linked",
      onClick: () => onApply({ link: filters.link === "linked" ? "all" : "linked" }),
    },
    {
      key: "unlinked",
      label: "Unlinked",
      value: unlinked,
      icon: <Link2Off className="h-4 w-4 text-amber-600" />,
      accent: "text-amber-700",
      active: filters.link === "unlinked",
      onClick: () => onApply({ link: filters.link === "unlinked" ? "all" : "unlinked" }),
    },
    {
      key: "missing",
      label: "Missing contact",
      value: missing,
      icon: <PhoneOff className="h-4 w-4 text-rose-600" />,
      accent: "text-rose-700",
      active: filters.contact === "no_phone",
      onClick: () => onApply({ contact: filters.contact === "no_phone" ? "all" : "no_phone" }),
    },
    {
      key: "tickets",
      label: "Open tickets",
      value: openTickets,
      icon: <Ticket className="h-4 w-4 text-sky-600" />,
      accent: "text-sky-700",
      active: filters.tickets === "open",
      onClick: () => onApply({ tickets: filters.tickets === "open" ? "all" : "open" }),
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
      {cards.map((card) => {
        const className = `flex items-center justify-between gap-2 rounded-lg border bg-surface px-3 py-2.5 text-left shadow-card transition-colors ${
          card.active
            ? "border-foreground/30 ring-1 ring-foreground/20"
            : "border-foreground/10 hover:bg-muted/50"
        }`;
        const inner = (
          <>
            <div className="min-w-0">
              <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                {card.icon}
                <span className="truncate">{card.label}</span>
              </p>
              <p className={`font-display mt-1 text-xl font-bold leading-none ${card.accent}`}>{card.value}</p>
            </div>
          </>
        );
        if (!card.onClick) {
          return (
            <div key={card.key} className={className}>
              {inner}
            </div>
          );
        }
        return (
          <button
            key={card.key}
            type="button"
            onClick={card.onClick}
            aria-pressed={card.active}
            className={`${className} focus:outline-none focus-visible:ring-2 focus-visible:ring-foreground/30`}
          >
            {inner}
          </button>
        );
      })}
    </div>
  );
}
