// Small presentational cards and drawers used by the overview panels.
import type { ReactNode } from "react";
import { AlertCircle, AlertTriangle, Clock3, Trophy, X } from "lucide-react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { useDismissibleLayer } from "@/shared/lib/useDismissibleLayer";
import { asNumber, asString } from "@/shared/lib/workspace";
import { ZoneKey, Candidate, closedCandidateStage } from "./shared";

export function Indicator({
  label,
  value,
  detail,
  tone = "neutral",
  onClick,
}: {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  tone?: "neutral" | "good" | "warn" | "bad" | "info";
  onClick?: () => void;
}) {
  const toneClass = {
    neutral: "border-border bg-surface text-foreground",
    info: "border-sky-200 bg-surface text-sky-800",
    good: "border-emerald-200 bg-surface text-emerald-800",
    warn: "border-amber-200 bg-surface text-amber-800",
    bad: "border-rose-200 bg-surface text-rose-800",
  }[tone];
  const className = `min-w-0 rounded-lg border px-2 py-1.5 text-left shadow-sm animate-in fade-in slide-in-from-bottom-1 duration-200 transition-[transform,box-shadow,border-color,background-color] hover:-translate-y-0.5 hover:border-foreground/20 hover:shadow-card-hover motion-reduce:animate-none motion-reduce:transition-none motion-reduce:hover:translate-y-0 sm:px-3 sm:py-2 ${toneClass}`;
  const content = (
    <>
      <p className="truncate text-[9px] font-bold uppercase leading-tight tracking-wide opacity-70 sm:text-[10px]">{label}</p>
      <p className="mt-1 truncate text-base font-bold leading-none text-current sm:text-xl">{value}</p>
      {detail ? <p className="mt-1 hidden truncate text-[11px] font-semibold text-muted-foreground sm:block">{detail}</p> : null}
    </>
  );
  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className={`${className} w-full cursor-pointer hover:bg-muted/60 focus:outline-none focus:ring-2 focus:ring-foreground/20`}
      >
        {content}
      </button>
    );
  }
  return (
    <div className={className}>
      {content}
    </div>
  );
}


export function ClosedCandidatesOverviewCard({
  candidates,
  onOpenRejected,
}: {
  candidates: Candidate[];
  onOpenRejected: () => void;
}) {
  const closedCandidates = candidates.filter((candidate) => {
    const status = asString(candidate.status) || "new";
    return ["rejected", "withdrawn"].includes(status);
  });

  if (!closedCandidates.length) {
    return null;
  }

  const stageGroups = [
    { key: "interview", label: "Interview", tone: "bg-amber-500" },
    { key: "math_test", label: "Math Test", tone: "bg-sky-500" },
    { key: "training", label: "Practice / Final", tone: "bg-violet-500" },
    { key: "withdrawn", label: "Withdrawn", tone: "bg-slate-500" },
    { key: "other", label: "Other", tone: "bg-zinc-500" },
  ]
    .map((stage) => ({
      ...stage,
      candidates: closedCandidates.filter((candidate) => closedCandidateStage(candidate) === stage.key),
    }))
    .filter((stage) => stage.candidates.length);

  return (
    <ChartCard
      title="Closed Candidates"
      subtitle="Where hiring candidates are dropping out"
      icon={<X className="h-4 w-4 text-info" />}
      headerActions={
        <button
          type="button"
          onClick={onOpenRejected}
          className="inline-flex h-8 items-center rounded-lg border border-foreground/10 bg-surface px-3 text-xs font-bold text-foreground hover:bg-muted"
        >
          Open Rejected Queue
        </button>
      }
    >
      <div className="rounded-lg border border-foreground/8 bg-background p-3">
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs font-semibold text-muted-foreground">Failure distribution</p>
          <span className="text-[11px] font-semibold text-muted-foreground">{closedCandidates.length} total</span>
        </div>
        <div className="mt-3 flex h-3 overflow-hidden rounded-full bg-muted">
          {stageGroups.map((stage) => {
            const percent = Math.round((stage.candidates.length / closedCandidates.length) * 100);
            return (
              <button
                key={`${stage.key}-bar`}
                type="button"
                onClick={onOpenRejected}
                className={`${stage.tone} h-full transition-opacity hover:opacity-85`}
                style={{ width: `${percent}%` }}
                title={`${stage.label}: ${stage.candidates.length}`}
              />
            );
          })}
        </div>
        <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {stageGroups.map((stage) => {
            const percent = Math.round((stage.candidates.length / closedCandidates.length) * 100);
            return (
              <div key={stage.key} className="rounded-lg border border-foreground/8 bg-surface p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={`h-2.5 w-2.5 rounded-full ${stage.tone}`} />
                      <span className="text-sm font-bold">{stage.label}</span>
                    </div>
                    <p className="mt-1 text-[11px] font-semibold text-muted-foreground">
                      {percent}% of closed candidates
                    </p>
                  </div>
                  <span className="text-sm font-bold">{stage.candidates.length}</span>
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {stage.candidates.map((candidate) => (
                    <button
                      type="button"
                      key={asNumber(candidate.id)}
                      onClick={onOpenRejected}
                      className="rounded-md bg-background px-2 py-1 text-[11px] font-semibold text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                    >
                      {asString(candidate.full_name)}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </ChartCard>
  );
}


export function HrAttentionCard({
  urgentItems,
  onOpenItem,
}: {
  urgentItems: Array<{
    candidateId: number;
    fullName: string;
    title: string;
    detail: string;
    tone: "bad" | "warn" | "info";
    tab: "hiring" | "training";
    filter?: "in_training" | "passed" | "rejected";
  }>;
  onOpenItem: (item: {
    candidateId: number;
    tab: "hiring" | "training";
    filter?: "in_training" | "passed" | "rejected";
  }) => void;
}) {
  return (
    <ChartCard title="Attention Needed" subtitle="Candidates that likely need action today" icon={<Clock3 className="h-4 w-4 text-info" />}>
      {urgentItems.length ? (
        <div className="grid min-h-[22rem] content-start gap-2">
          {urgentItems.map((item) => {
            const toneClass =
              item.tone === "bad"
                ? "border-rose-200 bg-rose-50"
                : item.tone === "warn"
                  ? "border-amber-200 bg-amber-50"
                  : "border-sky-200 bg-sky-50";
            return (
              <button
                key={`${item.candidateId}-${item.title}`}
                type="button"
                onClick={() => onOpenItem(item)}
                className={`rounded-lg border px-3 py-3 text-left transition-colors hover:bg-muted ${toneClass}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-bold">{item.fullName}</p>
                    <p className="mt-1 text-xs font-semibold text-foreground/80">{item.title}</p>
                    <p className="mt-1 text-[11px] text-muted-foreground">{item.detail}</p>
                  </div>
                  <span className="rounded-md bg-background px-2 py-1 text-[10px] font-bold text-muted-foreground">
                    Open
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      ) : (
        <div className="flex min-h-[22rem] items-center justify-center rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-8 text-center">
          <p className="text-sm font-bold">No urgent hiring blockers right now.</p>
        </div>
      )}
    </ChartCard>
  );
}


export function ZonesDrawer({
  zoneRows,
  activeTab,
  onTabChange,
  onClose,
}: {
  zoneRows: Record<ZoneKey, Array<Record<string, unknown>>>;
  activeTab: ZoneKey;
  onTabChange: (tab: ZoneKey) => void;
  onClose: () => void;
}) {
  const tabs: { key: ZoneKey; label: string; icon: ReactNode; color: string }[] = [
    { key: "green",  label: "Green",  icon: <Trophy className="h-3.5 w-3.5" />,         color: "text-success" },
    { key: "yellow", label: "Yellow", icon: <AlertTriangle className="h-3.5 w-3.5" />,  color: "text-warning" },
    { key: "red",    label: "Red",    icon: <AlertCircle className="h-3.5 w-3.5" />,    color: "text-destructive" },
  ];
  const rows = zoneRows[activeTab];
  const activeColor = tabs.find((t) => t.key === activeTab)?.color ?? "";
  useDismissibleLayer({ onDismiss: onClose, dismissOnOutsidePointer: false });

  return (
    <>
      <div className="fixed inset-0 z-40 bg-foreground/30 backdrop-blur-xs" onClick={onClose} role="presentation" />
      <div className="fixed inset-y-0 right-0 z-50 flex w-[min(24rem,100vw)] flex-col border-l border-foreground/10 bg-surface shadow-xl" role="dialog" aria-modal="true" aria-labelledby="performance-zones-title">
      <div className="flex shrink-0 items-center justify-between border-b border-foreground/8 px-5 py-3.5">
        <p id="performance-zones-title" className="text-sm font-bold">Performance Zones</p>
        <button type="button" onClick={onClose} className="flex h-11 w-11 items-center justify-center rounded-md hover:bg-foreground/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40" aria-label="Close performance zones">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="flex shrink-0 gap-0.5 border-b border-foreground/8 px-4 pt-2">
        {tabs.map(({ key, label, icon, color }) => {
          const count = zoneRows[key].length;
          const isActive = key === activeTab;
          return (
            <button
              key={key}
              type="button"
              onClick={() => onTabChange(key)}
              className={`flex items-center gap-1.5 rounded-t-md px-3 py-2 text-xs font-semibold transition-colors ${
                isActive
                  ? `border border-b-0 border-foreground/10 bg-background ${color}`
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <span>{icon}</span>
              {label}
              <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-bold ${isActive ? "bg-foreground/8" : "bg-foreground/5"}`}>
                {count}
              </span>
            </button>
          );
        })}
      </div>
      <div className="flex-1 overflow-y-auto overflow-x-auto">
        {rows.length ? (
          <table className="w-full text-left min-w-[320px]">
            <thead className="sticky top-0 z-20 bg-surface shadow-[0_1px_0_hsl(var(--foreground)/0.08)]">
              <tr className="border-b border-foreground/8">
                {["Group", "Subject", "AAP", "AR"].map((h) => (
                  <th key={h} className="px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${asString(row.group_name)}-${asString(row.subject_name)}`} className="border-b border-foreground/5 hover:bg-foreground/2">
                  <td className="px-4 py-2.5 text-xs font-semibold">{asString(row.group_name)}</td>
                  <td className="px-4 py-2.5 text-xs text-muted-foreground">{asString(row.subject_name)}</td>
                  <td className={`px-4 py-2.5 text-xs font-bold ${activeColor}`}>
                    {row.aap == null ? "-" : asNumber(row.aap).toFixed(1)}
                  </td>
                  <td className="px-4 py-2.5 text-xs">
                    {row.ar == null ? "-" : `${asNumber(row.ar).toFixed(1)}%`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="px-4 py-6 text-sm text-muted-foreground">No groups in this zone.</p>
        )}
      </div>
      </div>
    </>
  );
}


export function RoleMetric({
  label,
  value,
  detail,
  icon,
  tone = "bg-surface",
}: {
  label: string;
  value: string | number;
  detail: string;
  icon: ReactNode;
  tone?: string;
}) {
  return (
    <div className={`rounded-lg border border-foreground/8 px-3 py-3 shadow-card ${tone}`}>
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">{label}</span>
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-background text-foreground">{icon}</span>
      </div>
      <p className="text-2xl font-bold leading-none">{value}</p>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">{detail}</p>
    </div>
  );
}
