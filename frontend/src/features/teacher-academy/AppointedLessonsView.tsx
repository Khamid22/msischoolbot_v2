import { CalendarClock } from "lucide-react";
import type { ReactNode } from "react";

import { ActionMenu, type ActionMenuItem } from "@/shared/ui/ActionMenu";
import { EmptyState } from "@/shared/ui/EmptyState";
import { MobileCardList } from "@/shared/ui/MobileCardList";
import { ResponsiveTable } from "@/shared/ui/ResponsiveTable";
import { StatusBadge } from "@/shared/ui/StatusBadge";

export interface AppointedLessonCardModel {
  key: string;
  teacherName: string;
  subject: string;
  lessonTitle: string;
  dateLabel: string;
  evaluator: string;
  statusLabel: string;
  statusTone: "neutral" | "success" | "warning" | "danger" | "info";
  scoreText: string | null;
  onOpenTeacher: () => void;
  primaryAction: { label: string; icon: ReactNode; onClick: () => void } | null;
  menuActions: ActionMenuItem[];
}

function LessonActions({ item }: { item: AppointedLessonCardModel }) {
  return (
    <div className="flex items-center justify-end gap-2">
      {item.scoreText ? (
        <span className="inline-flex min-h-8 items-center rounded-lg bg-primary/10 px-2.5 text-xs font-black tabular-nums text-primary">
          {item.scoreText}
        </span>
      ) : null}
      {item.primaryAction ? (
        <button
          type="button"
          onClick={item.primaryAction.onClick}
          className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-xl bg-primary px-3 text-xs font-black text-primary-foreground hover:bg-primary/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
        >
          {item.primaryAction.icon}
          {item.primaryAction.label}
        </button>
      ) : null}
      {item.menuActions.length ? (
        <ActionMenu label={`Actions for ${item.teacherName}`} items={item.menuActions} />
      ) : null}
    </div>
  );
}

export function AppointedLessonsView({ items }: { items: AppointedLessonCardModel[] }) {
  if (!items.length) {
    return (
      <EmptyState
        icon={<CalendarClock className="h-6 w-6" />}
        title="No appointed lessons yet"
        detail="Appointed Teacher Academy lessons will appear here after lessons are selected for academy teachers."
        className="min-h-[22rem] rounded-2xl bg-card"
      />
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-card">
      <MobileCardList className="p-3 lg:hidden">
        {items.map((item) => (
          <article key={item.key} className="rounded-xl border border-border bg-background p-4 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 className="break-words font-display text-sm font-black text-foreground">{item.lessonTitle}</h2>
                <button
                  type="button"
                  onClick={item.onOpenTeacher}
                  className="mt-1 min-h-11 break-words text-left text-xs font-semibold text-muted-foreground hover:text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
                >
                  {item.teacherName} · {item.subject}
                </button>
              </div>
              <StatusBadge tone={item.statusTone} className="shrink-0 normal-case tracking-normal">
                {item.statusLabel}
              </StatusBadge>
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-3 border-t border-border pt-3 text-xs">
              <div>
                <dt className="font-black uppercase tracking-wide text-muted-foreground">Time</dt>
                <dd className="mt-1 font-bold text-foreground">{item.dateLabel}</dd>
              </div>
              <div>
                <dt className="font-black uppercase tracking-wide text-muted-foreground">Evaluator</dt>
                <dd className="mt-1 break-words font-bold text-foreground">{item.evaluator}</dd>
              </div>
            </dl>
            <div className="mt-3 border-t border-border pt-3">
              <LessonActions item={item} />
            </div>
          </article>
        ))}
      </MobileCardList>

      <ResponsiveTable showAt="lg" className="max-h-[calc(100dvh-18rem)]">
        <table className="w-full min-w-[60rem] table-fixed border-collapse text-left">
          <thead className="sticky top-0 z-10 border-b border-border bg-muted/80">
            <tr>
              {[
                ["Teacher", "18%"],
                ["Subject", "13%"],
                ["Appointed lesson", "21%"],
                ["Time", "12%"],
                ["Evaluator", "11%"],
                ["Status", "10%"],
                ["Actions", "15%"],
              ].map(([heading, width]) => (
                <th key={heading} scope="col" style={{ width }} className={`px-3 py-3 text-[0.6875rem] font-black uppercase tracking-wide text-muted-foreground ${heading === "Actions" ? "text-right" : ""}`}>
                  {heading}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {items.map((item) => (
              <tr key={item.key} className="bg-card transition-colors duration-150 hover:bg-muted/40 motion-reduce:transition-none">
                <td className="px-3 py-3">
                  <button type="button" onClick={item.onOpenTeacher} className="min-h-11 text-left text-sm font-black text-foreground hover:text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35">
                    {item.teacherName}
                  </button>
                </td>
                <td className="px-3 py-3 text-xs font-bold text-foreground">{item.subject}</td>
                <td className="px-3 py-3 text-xs font-black text-foreground">{item.lessonTitle}</td>
                <td className="px-3 py-3 text-xs font-semibold text-muted-foreground">{item.dateLabel}</td>
                <td className="px-3 py-3 text-xs font-semibold text-muted-foreground">{item.evaluator}</td>
                <td className="px-3 py-3">
                  <StatusBadge tone={item.statusTone} className="normal-case tracking-normal">{item.statusLabel}</StatusBadge>
                </td>
                <td className="px-3 py-3"><LessonActions item={item} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </ResponsiveTable>
    </div>
  );
}
