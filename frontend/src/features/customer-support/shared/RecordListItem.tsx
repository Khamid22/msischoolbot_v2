import { ChevronRight, GraduationCap, Link2, UsersRound } from "lucide-react";
import type { SupportRecordSummary } from "@/features/customer-support/model";
import { money } from "@/features/customer-support/shared/ui";
import { StatusBadge } from "@/shared/ui/StatusBadge";

export function RecordListItem({
  item,
  selected,
  onSelect,
}: {
  item: SupportRecordSummary;
  selected: boolean;
  onSelect: () => void;
}) {
  const Icon = item.kind === "student" ? GraduationCap : UsersRound;
  const linkLabel = item.linked_count
    ? item.kind === "student"
      ? `${item.linked_count} ${item.linked_count === 1 ? "parent" : "parents"}`
      : `${item.linked_count} ${item.linked_count === 1 ? "student" : "students"}`
    : item.kind === "student"
      ? "No linked parent"
      : "No linked student";

  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={`flex min-h-[6.25rem] w-full items-start gap-3 border-b border-border px-4 py-3 text-left transition-colors duration-150 last:border-b-0 hover:bg-muted/70 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/40 motion-reduce:transition-none ${selected ? "bg-primary/8" : "bg-card"}`}
    >
      <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${item.kind === "student" ? "bg-primary/10 text-primary" : "bg-emerald-50 text-emerald-700"}`}>
        <Icon className="h-5 w-5" aria-hidden="true" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex flex-wrap items-start justify-between gap-2">
          <span className="min-w-0 break-words text-sm font-black text-foreground">{item.display_name}</span>
          <StatusBadge status={item.status} className="shrink-0 text-[0.625rem]" />
        </span>
        <span className="mt-1 block break-words text-xs font-semibold text-muted-foreground">{item.secondary}</span>
        <span className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs font-bold text-muted-foreground">
          <span>{item.school_name}</span>
          {item.outstanding > 0 ? <span className="text-amber-700">Due {money(item.outstanding)}</span> : null}
          <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 ${item.linked_count ? "border-success/25 bg-success/10 text-success" : "border-warning/35 bg-warning/15 text-warning-foreground"}`}>
            <Link2 className="h-3 w-3" aria-hidden="true" />
            {linkLabel}
          </span>
        </span>
      </span>
      <ChevronRight className="mt-2 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
    </button>
  );
}
