import { useQuery } from "@tanstack/react-query";
import { useEffect, useState, type KeyboardEvent } from "react";

import { recruitmentRequest } from "@/features/recruitment/api";
import { dateLabel, humanize, type RecruitmentTask } from "@/features/recruitment/model";
import { RECRUITMENT_API, EmptyLine, PageState, queryError, rememberRecruitmentReturn, replaceUrlParams, restoreRecruitmentReturn } from "@/features/recruitment/ui";
import { StatusBadge } from "@/shared/ui/StatusBadge";

type TaskData = {
  items: RecruitmentTask[];
  groups: Record<string, RecruitmentTask[]>;
};

const taskTabs = ["open", "completed", "cancelled"] as const;
type TaskTab = (typeof taskTabs)[number];

export function TasksView({ basePath }: { basePath: string }) {
  const requested = new URLSearchParams(window.location.search).get("status") || "open";
  const [active, setActive] = useState<TaskTab>(taskTabs.includes(requested as TaskTab) ? requested as TaskTab : "open");
  const tasks = useQuery({ queryKey: ["recruitment", "tasks"], queryFn: () => recruitmentRequest<TaskData>(`${RECRUITMENT_API}/tasks`) });
  useEffect(() => {
    if (tasks.data) restoreRecruitmentReturn("tasks");
  }, [tasks.data]);
  if (tasks.isLoading) return <PageState>Loading tasks…</PageState>;
  if (tasks.error || !tasks.data) return <PageState tone="error">{queryError(tasks.error)}</PageState>;

  const tabItems: Record<TaskTab, RecruitmentTask[]> = {
    open: [...(tasks.data.groups.overdue || []), ...(tasks.data.groups.pending || [])],
    completed: tasks.data.groups.completed || [],
    cancelled: tasks.data.groups.cancelled || [],
  };
  const items = tabItems[active];
  const selectTab = (tab: TaskTab) => {
    setActive(tab);
    replaceUrlParams({ status: tab === "open" ? "" : tab });
  };
  const handleTabKeyDown = (event: KeyboardEvent<HTMLButtonElement>, tab: TaskTab) => {
    const current = taskTabs.indexOf(tab);
    const direction = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!direction) return;
    event.preventDefault();
    const next = taskTabs[(current + direction + taskTabs.length) % taskTabs.length];
    selectTab(next);
    requestAnimationFrame(() => document.getElementById(`task-tab-${next}`)?.focus());
  };

  return (
    <section className="overflow-hidden rounded-xl border border-border bg-card">
      <div className="flex gap-1 overflow-x-auto border-b border-border p-2" role="tablist" aria-label="Task status">
        {taskTabs.map((tab) => (
          <button
            key={tab}
            id={`task-tab-${tab}`}
            type="button"
            role="tab"
            tabIndex={active === tab ? 0 : -1}
            aria-selected={active === tab}
            aria-controls="task-status-panel"
            onClick={() => selectTab(tab)}
            onKeyDown={(event) => handleTabKeyDown(event, tab)}
            className={`inline-flex min-h-9 shrink-0 items-center gap-2 rounded-lg px-3 text-[13px] font-semibold focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${active === tab ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"}`}
          >
            {humanize(tab)}
            <span className={`rounded-full px-2 py-0.5 text-xs tabular-nums ${active === tab ? "bg-white/15" : "bg-muted"}`}>{tabItems[tab].length}</span>
          </button>
        ))}
      </div>
      <div id="task-status-panel" role="tabpanel" aria-labelledby={`task-tab-${active}`} className="divide-y divide-border">
        {items.map((task) => (
          <a
            key={task.id}
            href={`${basePath}/candidates/${task.candidate_id}?tab=activity&origin=tasks`}
            onClick={() => rememberRecruitmentReturn("tasks")}
            className="flex min-h-14 items-center justify-between gap-2 px-3 py-1.5 transition-colors hover:bg-muted/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/30"
          >
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">{task.title}</p>
              <p className="mt-0.5 truncate text-xs text-muted-foreground">{task.candidate_name} · {dateLabel(task.due_at)}</p>
            </div>
            <StatusBadge status={task.effective_status} />
          </a>
        ))}
        {!items.length ? <div className="p-3"><EmptyLine>No {active} tasks.</EmptyLine></div> : null}
      </div>
    </section>
  );
}
