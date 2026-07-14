// Small presentational cards and drawers used by the overview panels.
import type { ReactNode } from "react";
import { AlertCircle, AlertTriangle, Clock3, Trophy, X } from "lucide-react";
import { useDismissibleLayer } from "@/shared/lib/useDismissibleLayer";
import { asNumber, asString } from "@/shared/lib/workspace";
import { ZoneKey } from "./shared";

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
