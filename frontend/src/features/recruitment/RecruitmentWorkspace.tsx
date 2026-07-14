import {
  Activity,
  ArrowLeft,
  BriefcaseBusiness,
  CalendarClock,
  CheckCircle2,
  ClipboardCheck,
  FileText,
  KanbanSquare,
  ListFilter,
  Loader2,
  MessageSquareText,
  Plus,
  Search,
  ShieldCheck,
  UserRound,
  UsersRound,
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState, type FormEvent, type ReactNode } from "react";

import { recruitmentRequest, formValues, jsonBody } from "@/features/recruitment/api";
import {
  alternativeStages,
  dateLabel,
  humanize,
  manualStages,
  primaryStages,
  stageLabels,
  type RecruitmentCandidate,
  type RecruitmentOptions,
  type RecruitmentRole,
  type RecruitmentTask,
  type RecruitmentView,
} from "@/features/recruitment/model";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";
import { Pagination } from "@/shared/ui/Pagination";
import { RoleWorkspaceShell } from "@/shared/ui/RoleWorkspaceShell";
import { StatusBadge } from "@/shared/ui/StatusBadge";

const API = "/api/v1/recruitment";
const fieldClass =
  "min-h-11 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none transition focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/20";
const buttonClass =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-bold text-primary-foreground transition hover:brightness-105 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:cursor-not-allowed disabled:opacity-50";
const secondaryButtonClass =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-border bg-card px-4 py-2 text-sm font-bold text-foreground transition hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:cursor-not-allowed disabled:opacity-50";

type Props = {
  authLogin?: string;
  authRole?: string;
  role?: RecruitmentRole;
  view?: RecruitmentView;
  basePath?: string;
  candidateId?: number | string | null;
  csrfToken?: string;
};

type PipelineData = {
  stages: Record<string, RecruitmentCandidate[]>;
  counts: Record<string, number>;
  total: number;
};

type CandidateListData = {
  items: RecruitmentCandidate[];
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
};

type TaskData = {
  items: RecruitmentTask[];
  groups: Record<string, RecruitmentTask[]>;
};

type MutationPayload = { message: string; candidate?: RecruitmentCandidate };

function roleLabel(role: string) {
  return {
    hr_manager: "HR Manager",
    academic_director: "Academic Director",
    head_of_department: "Head of Department",
    system_admin: "System Admin",
    admin: "Admin",
    ceo: "CEO",
  }[role] || "Recruitment";
}

function workspaceHome(role: string) {
  return {
    hr_manager: "/hr-manager",
    academic_director: "/academic-director",
    head_of_department: "/head-of-departments",
    system_admin: "/internal/operations",
    admin: "/internal/operations",
    ceo: "/ceo",
  }[role] || "/";
}

function queryError(error: unknown) {
  return error instanceof Error ? error.message : "Unable to load recruitment data.";
}

function PageState({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "error" }) {
  return (
    <div
      className={`rounded-xl border p-5 text-sm ${tone === "error" ? "border-destructive/30 bg-destructive/5 text-destructive" : "border-border bg-card text-muted-foreground"}`}
    >
      {children}
    </div>
  );
}

function Section({ id, title, icon, children, action }: { id: string; title: string; icon: ReactNode; children: ReactNode; action?: ReactNode }) {
  return (
    <section id={id} className="scroll-mt-24 rounded-xl border border-border bg-card shadow-sm">
      <div className="flex min-h-14 flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
        <h2 className="flex items-center gap-2 text-sm font-black text-foreground">
          {icon}
          {title}
        </h2>
        {action}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

function DefinitionGrid({ values }: { values: Array<[string, unknown]> }) {
  return (
    <dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {values.map(([label, value]) => (
        <div key={label} className="min-w-0 rounded-lg bg-muted/45 p-3">
          <dt className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">{label}</dt>
          <dd className="mt-1 break-words text-sm font-semibold text-foreground">{String(value || "Not set")}</dd>
        </div>
      ))}
    </dl>
  );
}

function EmptyLine({ children }: { children: ReactNode }) {
  return <p className="rounded-lg border border-dashed border-border px-3 py-4 text-sm text-muted-foreground">{children}</p>;
}

function CandidateCard({ candidate, basePath, canMove, onMove }: {
  candidate: RecruitmentCandidate;
  basePath: string;
  canMove: boolean;
  onMove: (candidate: RecruitmentCandidate, stage: string) => void;
}) {
  return (
    <article
      draggable={canMove}
      onDragStart={(event) => {
        event.dataTransfer.setData("application/x-msi-recruitment", JSON.stringify({ id: candidate.id, version: candidate.version }));
        event.dataTransfer.effectAllowed = "move";
      }}
      className="rounded-xl border border-border bg-card p-3 shadow-sm transition hover:border-primary/30 hover:shadow-md focus-within:ring-2 focus-within:ring-primary/25"
    >
      <div className="flex items-start justify-between gap-2">
        <a href={`${basePath}/candidates/${candidate.id}`} className="min-w-0 rounded font-black text-foreground hover:text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30">
          {candidate.full_name}
        </a>
        <span className="shrink-0 text-[10px] font-bold text-muted-foreground">#{candidate.id}</span>
      </div>
      <p className="mt-1 truncate text-xs text-muted-foreground">{candidate.applied_position || candidate.subject || "Position not set"}</p>
      {candidate.next_task ? (
        <div className="mt-3 rounded-lg bg-muted/60 px-2.5 py-2 text-xs">
          <p className="font-bold text-foreground">{candidate.next_task.title}</p>
          <p className="mt-0.5 text-muted-foreground">{dateLabel(candidate.next_task.due_at)}</p>
        </div>
      ) : null}
      {canMove ? (
        <label className="mt-3 block text-[11px] font-bold text-muted-foreground">
          Move candidate
          <select
            className={`${fieldClass} mt-1`}
            value=""
            onChange={(event) => {
              if (event.target.value) onMove(candidate, event.target.value);
              event.target.value = "";
            }}
          >
            <option value="">Choose stage…</option>
            {manualStages.filter((stage) => stage !== candidate.status).map((stage) => (
              <option key={stage} value={stage}>{stageLabels[stage]}</option>
            ))}
          </select>
        </label>
      ) : null}
    </article>
  );
}

function PipelineView({ basePath, onAnnouncement }: { basePath: string; onAnnouncement: (message: string) => void }) {
  const queryClient = useQueryClient();
  const pipeline = useQuery({
    queryKey: ["recruitment", "pipeline"],
    queryFn: () => recruitmentRequest<PipelineData>(`${API}/pipeline`),
  });
  const move = useMutation({
    mutationFn: ({ candidate, stage }: { candidate: RecruitmentCandidate; stage: string }) =>
      recruitmentRequest<MutationPayload>(`${API}/candidates/${candidate.id}/stage`, {
        method: "POST",
        body: jsonBody({ stage, expected_version: candidate.version, reason: "Pipeline move" }),
      }),
    onMutate: async ({ candidate, stage }) => {
      await queryClient.cancelQueries({ queryKey: ["recruitment", "pipeline"] });
      const previous = queryClient.getQueryData<PipelineData>(["recruitment", "pipeline"]);
      if (previous) {
        const stages = Object.fromEntries(
          Object.entries(previous.stages).map(([key, items]) => [key, items.filter((item) => item.id !== candidate.id)]),
        );
        stages[stage] = [{ ...candidate, status: stage, version: candidate.version + 1 }, ...(stages[stage] || [])];
        queryClient.setQueryData(["recruitment", "pipeline"], { ...previous, stages });
      }
      return { previous };
    },
    onError: (error, _variables, context) => {
      if (context?.previous) queryClient.setQueryData(["recruitment", "pipeline"], context.previous);
      onAnnouncement(`Move failed. ${queryError(error)}`);
    },
    onSuccess: (result) => onAnnouncement(result.message || "Candidate moved."),
    onSettled: () => void queryClient.invalidateQueries({ queryKey: ["recruitment"] }),
  });

  if (pipeline.isLoading) return <PageState>Loading recruitment pipeline…</PageState>;
  if (pipeline.error || !pipeline.data) return <PageState tone="error">{queryError(pipeline.error)}</PageState>;
  const sample = Object.values(pipeline.data.stages).flat()[0];
  const canMove = Boolean(sample?.permissions?.can_move_stage);

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto pb-2">
        <div className="grid min-w-[1180px] grid-cols-6 gap-3">
          {primaryStages.map((stage) => {
            const acceptsDrop = canMove && manualStages.includes(stage as (typeof manualStages)[number]);
            const items = pipeline.data.stages[stage] || [];
            return (
              <section
                key={stage}
                aria-label={`${stageLabels[stage]} candidates`}
                onDragOver={(event) => {
                  if (acceptsDrop) event.preventDefault();
                }}
                onDrop={(event) => {
                  if (!acceptsDrop) return;
                  event.preventDefault();
                  try {
                    const value = JSON.parse(event.dataTransfer.getData("application/x-msi-recruitment"));
                    const candidate = Object.values(pipeline.data.stages).flat().find((item) => item.id === Number(value.id));
                    if (candidate && candidate.status !== stage) move.mutate({ candidate, stage });
                  } catch {
                    onAnnouncement("The dragged candidate could not be read.");
                  }
                }}
                className="min-h-[28rem] rounded-xl border border-border bg-muted/30 p-2"
              >
                <div className="mb-2 flex min-h-11 items-center justify-between gap-2 px-1">
                  <h2 className="text-xs font-black uppercase tracking-wide text-foreground">{stageLabels[stage]}</h2>
                  <span className="rounded-full bg-card px-2 py-1 text-[11px] font-black text-muted-foreground">{items.length}</span>
                </div>
                <div className="space-y-2">
                  {items.map((candidate) => (
                    <CandidateCard
                      key={candidate.id}
                      candidate={candidate}
                      basePath={basePath}
                      canMove={Boolean(candidate.permissions?.can_move_stage) && !["teacher_academy", "active_teacher"].includes(candidate.status)}
                      onMove={(item, nextStage) => move.mutate({ candidate: item, stage: nextStage })}
                    />
                  ))}
                  {!items.length ? <p className="px-2 py-4 text-center text-xs text-muted-foreground">No candidates</p> : null}
                </div>
              </section>
            );
          })}
        </div>
      </div>
      <section className="rounded-xl border border-border bg-card p-4">
        <h2 className="text-sm font-black text-foreground">Alternative outcomes</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          {alternativeStages.map((stage) => (
            <a key={stage} href={`${basePath}/candidates?stage=${stage}`} className="flex min-h-14 items-center justify-between rounded-lg border border-border px-3 text-sm font-bold hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30">
              <span>{stageLabels[stage]}</span>
              <span className="rounded-full bg-muted px-2 py-1 text-xs">{pipeline.data.counts[stage] || 0}</span>
            </a>
          ))}
        </div>
      </section>
    </div>
  );
}

function CandidateListView({ basePath }: { basePath: string }) {
  const initialStage = new URLSearchParams(window.location.search).get("stage") || "";
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ search: "", position: "", stage: initialStage, source: "", application_from: "", application_to: "", final_decision: "", evaluator_account_id: "" });
  const options = useQuery({ queryKey: ["recruitment", "options"], queryFn: () => recruitmentRequest<RecruitmentOptions>(`${API}/options`) });
  const params = new URLSearchParams({ page: String(page), per_page: "25" });
  Object.entries(filters).forEach(([key, value]) => { if (value) params.set(key, value); });
  const candidates = useQuery({
    queryKey: ["recruitment", "candidates", page, filters],
    queryFn: () => recruitmentRequest<CandidateListData>(`${API}/candidates?${params}`),
  });

  return (
    <div className="space-y-4">
      <div className="grid gap-3 rounded-xl border border-border bg-card p-4 sm:grid-cols-2 lg:grid-cols-4">
        <label className="text-xs font-bold text-muted-foreground sm:col-span-2">
          Search by name
          <span className="relative mt-1 block">
            <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4" />
            <input className={`${fieldClass} pl-9`} value={filters.search} onChange={(event) => { setPage(1); setFilters({ ...filters, search: event.target.value }); }} placeholder="Candidate name" />
          </span>
        </label>
        <label className="text-xs font-bold text-muted-foreground">Position<input className={`${fieldClass} mt-1`} value={filters.position} onChange={(event) => { setPage(1); setFilters({ ...filters, position: event.target.value }); }} /></label>
        <label className="text-xs font-bold text-muted-foreground">Stage<select className={`${fieldClass} mt-1`} value={filters.stage} onChange={(event) => { setPage(1); setFilters({ ...filters, stage: event.target.value }); }}><option value="">All stages</option>{options.data?.stages.map((stage) => <option key={stage} value={stage}>{stageLabels[stage] || humanize(stage)}</option>)}</select></label>
        <label className="text-xs font-bold text-muted-foreground">Source<select className={`${fieldClass} mt-1`} value={filters.source} onChange={(event) => { setPage(1); setFilters({ ...filters, source: event.target.value }); }}><option value="">All sources</option>{options.data?.sources.map((source) => <option key={source}>{source}</option>)}</select></label>
        <label className="text-xs font-bold text-muted-foreground">Final outcome<select className={`${fieldClass} mt-1`} value={filters.final_decision} onChange={(event) => { setPage(1); setFilters({ ...filters, final_decision: event.target.value }); }}><option value="">All outcomes</option>{["teacher_academy", "active_teacher", "rejected", "on_hold", "candidate_withdrew"].map((outcome) => <option key={outcome} value={outcome}>{stageLabels[outcome]}</option>)}</select></label>
        <label className="text-xs font-bold text-muted-foreground">Applied from<input type="date" className={`${fieldClass} mt-1`} value={filters.application_from} onChange={(event) => { setPage(1); setFilters({ ...filters, application_from: event.target.value }); }} /></label>
        <label className="text-xs font-bold text-muted-foreground">Applied to<input type="date" className={`${fieldClass} mt-1`} value={filters.application_to} onChange={(event) => { setPage(1); setFilters({ ...filters, application_to: event.target.value }); }} /></label>
        <label className="text-xs font-bold text-muted-foreground">Evaluator<select className={`${fieldClass} mt-1`} value={filters.evaluator_account_id} onChange={(event) => { setPage(1); setFilters({ ...filters, evaluator_account_id: event.target.value }); }}><option value="">All evaluators</option>{options.data?.staff.filter((person) => ["academic_director", "head_of_department"].includes(person.role)).map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}</select></label>
      </div>
      {candidates.isLoading ? <PageState>Loading candidates…</PageState> : null}
      {candidates.error ? <PageState tone="error">{queryError(candidates.error)}</PageState> : null}
      {candidates.data ? (
        <section className="overflow-hidden rounded-xl border border-border bg-card">
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-muted/60 text-xs uppercase tracking-wide text-muted-foreground"><tr><th className="px-4 py-3">Candidate</th><th className="px-4 py-3">Position</th><th className="px-4 py-3">Stage</th><th className="px-4 py-3">Applied</th><th className="px-4 py-3">Next action</th></tr></thead>
              <tbody className="divide-y divide-border">{candidates.data.items.map((candidate) => <tr key={candidate.id} className="hover:bg-muted/30"><td className="px-4 py-3"><a className="font-black hover:text-primary" href={`${basePath}/candidates/${candidate.id}`}>{candidate.full_name}</a><p className="text-xs text-muted-foreground">{candidate.phone || "No phone"}</p></td><td className="px-4 py-3">{candidate.applied_position || candidate.subject || "—"}</td><td className="px-4 py-3"><StatusBadge status={candidate.status}>{stageLabels[candidate.status] || humanize(candidate.status)}</StatusBadge></td><td className="px-4 py-3">{dateLabel(candidate.application_date)}</td><td className="px-4 py-3">{candidate.next_task?.title || "—"}</td></tr>)}</tbody>
            </table>
          </div>
          <div className="divide-y divide-border md:hidden">{candidates.data.items.map((candidate) => <a key={candidate.id} href={`${basePath}/candidates/${candidate.id}`} className="block min-h-14 p-4 hover:bg-muted/40"><div className="flex items-start justify-between gap-2"><span className="font-black">{candidate.full_name}</span><StatusBadge status={candidate.status}>{stageLabels[candidate.status]}</StatusBadge></div><p className="mt-1 text-xs text-muted-foreground">{candidate.applied_position || "Position not set"}</p></a>)}</div>
          {!candidates.data.items.length ? <div className="p-4"><EmptyLine>No candidates match these filters.</EmptyLine></div> : null}
          <div className="p-4"><Pagination page={page} totalPages={candidates.data.total_pages} onPageChange={setPage} label={`${candidates.data.total} candidates · Page ${page} of ${candidates.data.total_pages}`} /></div>
        </section>
      ) : null}
    </div>
  );
}

function TasksView({ basePath }: { basePath: string }) {
  const tasks = useQuery({ queryKey: ["recruitment", "tasks"], queryFn: () => recruitmentRequest<TaskData>(`${API}/tasks`) });
  if (tasks.isLoading) return <PageState>Loading tasks…</PageState>;
  if (tasks.error || !tasks.data) return <PageState tone="error">{queryError(tasks.error)}</PageState>;
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {["overdue", "pending", "completed", "cancelled"].map((status) => (
        <section key={status} className="rounded-xl border border-border bg-card p-4">
          <div className="mb-3 flex items-center justify-between"><h2 className="font-black">{humanize(status)}</h2><span className="rounded-full bg-muted px-2 py-1 text-xs font-black">{tasks.data.groups[status]?.length || 0}</span></div>
          <div className="space-y-2">{(tasks.data.groups[status] || []).map((task) => <a key={task.id} href={`${basePath}/candidates/${task.candidate_id}#tasks`} className="block min-h-14 rounded-lg border border-border p-3 hover:bg-muted/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"><p className="font-bold">{task.title}</p><p className="mt-1 text-xs text-muted-foreground">{task.candidate_name} · {dateLabel(task.due_at)}</p></a>)}{!(tasks.data.groups[status] || []).length ? <EmptyLine>No {status} tasks.</EmptyLine> : null}</div>
        </section>
      ))}
    </div>
  );
}

function SimpleForm({ title, submitLabel, fields, onSubmit, pending }: {
  title: string;
  submitLabel: string;
  fields: ReactNode;
  onSubmit: (values: Record<string, string | number | null>, form: HTMLFormElement) => void;
  pending: boolean;
}) {
  return (
    <details className="rounded-lg border border-border bg-background">
      <summary className="min-h-11 cursor-pointer list-none px-3 py-3 text-sm font-bold focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30">{title}</summary>
      <form className="grid gap-3 border-t border-border p-3" onSubmit={(event) => { event.preventDefault(); onSubmit(formValues(event.currentTarget), event.currentTarget); }}>
        {fields}
        <button className={buttonClass} disabled={pending} type="submit">{pending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}{submitLabel}</button>
      </form>
    </details>
  );
}

function AttemptList({ items, empty }: { items: Array<Record<string, unknown>>; empty: string }) {
  if (!items.length) return <EmptyLine>{empty}</EmptyLine>;
  return <div className="space-y-2">{items.map((item, index) => <article key={Number(item.id || index)} className="rounded-lg border border-border p-3"><div className="flex flex-wrap items-center justify-between gap-2"><StatusBadge status={String(item.result || "recorded")} /><span className="text-xs text-muted-foreground">{dateLabel(item.interview_at || item.test_at || item.demo_at || item.created_at)}</span></div>{item.score !== null && item.score !== undefined ? <p className="mt-2 text-sm font-black">Score: {String(item.score)}{item.maximum_score ? ` / ${String(item.maximum_score)} (${String(item.percentage || 0)}%)` : " / 10"}</p> : null}<p className="mt-2 whitespace-pre-wrap text-sm text-muted-foreground">{String(item.notes || item.overview || item.recommendation || "No notes")}</p></article>)}</div>;
}

function CandidateProfile({ candidateId, basePath, role, onAnnouncement }: { candidateId: number; basePath: string; role: string; onAnnouncement: (message: string) => void }) {
  const queryClient = useQueryClient();
  const detail = useQuery({ queryKey: ["recruitment", "candidate", candidateId], queryFn: () => recruitmentRequest<RecruitmentCandidate>(`${API}/candidates/${candidateId}`) });
  const options = useQuery({ queryKey: ["recruitment", "options"], queryFn: () => recruitmentRequest<RecruitmentOptions>(`${API}/options`) });
  const mutation = useMutation({
    mutationFn: ({ url, method = "POST", values, formData }: { url: string; method?: string; values?: unknown; formData?: FormData }) => recruitmentRequest<MutationPayload>(url, { method, body: formData || jsonBody(values || {}) }),
    onSuccess: (result) => {
      onAnnouncement(result.message || "Recruitment record saved.");
      if (result.candidate) queryClient.setQueryData(["recruitment", "candidate", candidateId], result.candidate);
      void queryClient.invalidateQueries({ queryKey: ["recruitment"] });
    },
    onError: (error) => onAnnouncement(queryError(error)),
  });
  const submit = (path: string, values: unknown, method = "POST") => mutation.mutate({ url: `${API}/candidates/${candidateId}${path}`, method, values });

  if (detail.isLoading) return <PageState>Loading candidate profile…</PageState>;
  if (detail.error || !detail.data) return <PageState tone="error">{queryError(detail.error)}</PageState>;
  const candidate = detail.data;
  const permissions = candidate.permissions;
  const approved = (candidate.approvals || []).filter((item) => item.status === "approved");
  const pendingApprovals = (candidate.approvals || []).filter((item) => item.status === "requested");

  return (
    <div className="space-y-4">
      <header className="rounded-xl border border-border bg-card p-4 shadow-sm">
        <a href={`${basePath}/candidates`} className="inline-flex min-h-11 items-center gap-2 rounded-lg text-sm font-bold text-muted-foreground hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"><ArrowLeft className="h-4 w-4" />All candidates</a>
        <div className="mt-2 flex flex-wrap items-start justify-between gap-3"><div><h1 className="text-2xl font-black tracking-tight">{candidate.full_name}</h1><p className="mt-1 text-sm text-muted-foreground">#{candidate.id} · {candidate.applied_position || candidate.subject || "Position not set"}</p></div><StatusBadge status={candidate.status}>{stageLabels[candidate.status] || humanize(candidate.status)}</StatusBadge></div>
        <nav aria-label="Candidate profile sections" className="mt-4 flex gap-2 overflow-x-auto pb-1 text-xs font-bold">{[["personal", "Personal"], ["documents", "Documents"], ["assessments", "Assessments"], ["review", "Review"], ["tasks", "Tasks"], ["notes", "Notes"], ["activity", "Activity"]].map(([id, label]) => <a key={id} href={`#${id}`} className="inline-flex min-h-11 shrink-0 items-center rounded-lg border border-border px-3 hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30">{label}</a>)}</nav>
      </header>

      <Section id="personal" title="Personal & background" icon={<UserRound className="h-4 w-4" />}>
        <DefinitionGrid values={[
          ["Phone", candidate.phone], ["Telegram", candidate.telegram_username], ["Application date", dateLabel(candidate.application_date)],
          ["Source", candidate.source], ["Age", candidate.age], ["Address", candidate.address], ["English", candidate.english_level],
          ["Preferred schedule", candidate.preferred_schedule], ["Availability", candidate.employment_availability], ["Start date", dateLabel(candidate.available_start_date)],
          ["Expected salary", candidate.expected_salary_uzs ? `${Number(candidate.expected_salary_uzs).toLocaleString()} UZS` : ""], ["Previous workplace", candidate.previous_workplace],
        ]} />
        <div className="mt-3"><DefinitionGrid values={[["Motivation & expectations", candidate.motivation_expectations], ["Work experience", candidate.work_experience], ["Teaching experience", candidate.teaching_experience], ["Interests & hobbies", candidate.interests_hobbies]]} /></div>
        {permissions?.can_edit_profile ? (
          <div className="mt-4"><SimpleForm title="Edit personal and background data" submitLabel="Save profile" pending={mutation.isPending} onSubmit={(values) => submit("", Object.fromEntries(Object.entries(values).filter(([, value]) => value !== "")), "PATCH")} fields={<div className="grid gap-3 sm:grid-cols-2"><label className="text-xs font-bold">Full name<input name="full_name" defaultValue={candidate.full_name} required className={`${fieldClass} mt-1`} /></label><label className="text-xs font-bold">Phone<input name="phone" defaultValue={candidate.phone} className={`${fieldClass} mt-1`} /></label><label className="text-xs font-bold">Position<input name="applied_position" defaultValue={candidate.applied_position} className={`${fieldClass} mt-1`} /></label><label className="text-xs font-bold">Source<select name="source" defaultValue={candidate.source} className={`${fieldClass} mt-1`}><option value="">Not set</option>{options.data?.sources.map((source) => <option key={source}>{source}</option>)}</select></label><label className="text-xs font-bold">Age<input name="age" type="number" min="14" max="100" defaultValue={candidate.age || ""} className={`${fieldClass} mt-1`} /></label><label className="text-xs font-bold">English level<input name="english_level" defaultValue={candidate.english_level} className={`${fieldClass} mt-1`} /></label><label className="text-xs font-bold sm:col-span-2">Address<textarea name="address" defaultValue={candidate.address} className={`${fieldClass} mt-1`} /></label><label className="text-xs font-bold sm:col-span-2">Work experience<textarea name="work_experience" defaultValue={candidate.work_experience} className={`${fieldClass} mt-1`} /></label><label className="text-xs font-bold sm:col-span-2">Teaching experience<textarea name="teaching_experience" defaultValue={candidate.teaching_experience} className={`${fieldClass} mt-1`} /></label></div>} /></div>
        ) : null}
      </Section>

      <Section id="documents" title="Documents" icon={<FileText className="h-4 w-4" />} action={<span className="text-xs text-muted-foreground">Missing: {candidate.missing_document_types?.length || 0}</span>}>
        <div className="grid gap-2 sm:grid-cols-2">{(candidate.documents || []).map((document) => <div key={Number(document.id)} className="flex min-h-14 items-center justify-between gap-2 rounded-lg border border-border p-3"><div className="min-w-0"><p className="truncate text-sm font-bold">{String(document.original_file_name)}</p><p className="text-xs text-muted-foreground">{humanize(document.document_type)} · v{String(document.version)}</p></div><div className="flex shrink-0 gap-1"><a target="_blank" rel="noreferrer" href={`${API}/candidates/${candidateId}/documents/${String(document.id)}/open`} className={secondaryButtonClass}>Open</a>{permissions?.can_manage_documents ? <button className={secondaryButtonClass} type="button" onClick={() => mutation.mutate({ url: `${API}/candidates/${candidateId}/documents/${String(document.id)}`, method: "DELETE" })}>Remove</button> : null}</div></div>)}</div>
        {!(candidate.documents || []).length ? <EmptyLine>No documents uploaded.</EmptyLine> : null}
        <p className="mt-3 text-xs text-muted-foreground">Missing document types are informational and never block a stage move: {(candidate.missing_document_types || []).map(humanize).join(", ") || "none"}.</p>
        {permissions?.can_manage_documents ? <form className="mt-4 grid gap-3 rounded-lg border border-border p-3 sm:grid-cols-[1fr_1fr_auto]" onSubmit={(event) => { event.preventDefault(); const data = new FormData(event.currentTarget); mutation.mutate({ url: `${API}/candidates/${candidateId}/documents`, method: "POST", formData: data }); }}><label className="text-xs font-bold">Document type<select name="document_type" required className={`${fieldClass} mt-1`}>{options.data?.document_types.map((type) => <option key={type} value={type}>{humanize(type)}</option>)}</select></label><label className="text-xs font-bold">PDF, DOC/DOCX, JPG or PNG (max 20 MB)<input name="document" required type="file" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" className={`${fieldClass} mt-1 file:mr-2 file:border-0 file:bg-transparent file:font-bold`} /></label><button disabled={!options.data?.document_upload_enabled || mutation.isPending} className={`${buttonClass} self-end`} type="submit">Upload</button>{!options.data?.document_upload_enabled ? <p className="text-xs text-muted-foreground sm:col-span-3">Storage is not configured. The pipeline remains available; uploads are temporarily disabled.</p> : null}</form> : null}
      </Section>

      <Section id="assessments" title="Interviews, tests & demos" icon={<ClipboardCheck className="h-4 w-4" />}>
        <div className="grid gap-4 xl:grid-cols-3"><div><h3 className="mb-2 text-sm font-black">Interviews</h3><AttemptList items={candidate.interviews || []} empty="No interviews recorded." />{permissions?.can_manage_interviews ? <div className="mt-3"><SimpleForm title="Record interview" submitLabel="Save interview" pending={mutation.isPending} onSubmit={(values, form) => { submit("/interviews", values); form.reset(); }} fields={<><label className="text-xs font-bold">Result<select required name="result" className={`${fieldClass} mt-1`}><option value="passed">Passed</option><option value="failed">Failed</option><option value="on_hold">On hold</option><option value="additional_interview">Additional interview</option><option value="candidate_withdrew">Candidate withdrew</option></select></label><label className="text-xs font-bold">Format<input name="interview_format" className={`${fieldClass} mt-1`} /></label><label className="text-xs font-bold">Notes<textarea name="notes" className={`${fieldClass} mt-1`} /></label><label className="text-xs font-bold">HR recommendation<textarea name="hr_recommendation" className={`${fieldClass} mt-1`} /></label></>} /></div> : null}</div><div><h3 className="mb-2 text-sm font-black">Subject tests</h3><AttemptList items={candidate.subject_tests || []} empty="No subject tests recorded." />{permissions?.can_add_academic_evaluation ? <div className="mt-3"><SimpleForm title="Record subject test" submitLabel="Save test" pending={mutation.isPending} onSubmit={(values, form) => { submit("/subject-tests", { ...values, subject_id: candidate.subject_id || null }); form.reset(); }} fields={<><label className="text-xs font-bold">Score<input name="score" type="number" min="0" step="0.01" className={`${fieldClass} mt-1`} /></label><label className="text-xs font-bold">Maximum score<input name="maximum_score" type="number" min="0.01" step="0.01" className={`${fieldClass} mt-1`} /></label><label className="text-xs font-bold">Result<select name="result" className={`${fieldClass} mt-1`}><option value="passed">Passed</option><option value="failed">Failed</option><option value="retake_required">Retake required</option><option value="not_completed">Not completed</option></select></label><label className="text-xs font-bold">Notes<textarea name="notes" className={`${fieldClass} mt-1`} /></label></>} /></div> : null}</div><div><h3 className="mb-2 text-sm font-black">Demo lessons</h3><AttemptList items={candidate.demo_lessons || []} empty="No demo lessons recorded." />{permissions?.can_add_academic_evaluation ? <div className="mt-3"><SimpleForm title="Record demo lesson" submitLabel="Save demo" pending={mutation.isPending} onSubmit={(values, form) => { submit("/demo-lessons", { ...values, subject_id: candidate.subject_id || null }); form.reset(); }} fields={<><label className="text-xs font-bold">Topic<input name="topic" className={`${fieldClass} mt-1`} /></label><label className="text-xs font-bold">Score (0–10)<input name="score" type="number" min="0" max="10" step="0.01" className={`${fieldClass} mt-1`} /></label><label className="text-xs font-bold">Result<select name="result" className={`${fieldClass} mt-1`}><option value="passed">Passed</option><option value="failed">Failed</option><option value="additional_demo">Additional demo</option><option value="on_hold">On hold</option></select></label><label className="text-xs font-bold">Overview<textarea name="overview" className={`${fieldClass} mt-1`} /></label><label className="text-xs font-bold">Academic recommendation<textarea name="recommendation" className={`${fieldClass} mt-1`} /></label></>} /></div> : null}</div></div>
      </Section>

      <Section id="review" title="Under review, approval & final decision" icon={<ShieldCheck className="h-4 w-4" />}>
        <DefinitionGrid values={Object.entries(candidate.under_review || {}).map(([key, value]) => [humanize(key), value])} />
        {permissions?.can_manage_assignments ? <div className="mt-4"><SimpleForm title="Assign Academic Director / HOD" submitLabel="Save assignments" pending={mutation.isPending} onSubmit={(values) => { const ids = String(values.assignee_account_ids || "").split(",").map(Number).filter(Boolean); submit("/assignments", { assignee_account_ids: ids, subject_id: candidate.subject_id || null }, "PUT"); }} fields={<label className="text-xs font-bold">Evaluator account IDs (comma-separated)<input name="assignee_account_ids" defaultValue={(candidate.assignments || []).map((item) => item.assignee_account_id).join(",")} className={`${fieldClass} mt-1`} list="recruitment-evaluators" /><datalist id="recruitment-evaluators">{options.data?.staff.filter((person) => ["academic_director", "head_of_department"].includes(person.role)).map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}</datalist></label>} /></div> : null}
        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          <div className="space-y-2"><h3 className="text-sm font-black">Approval requests</h3>{(candidate.approvals || []).map((item) => <article key={Number(item.id)} className="rounded-lg border border-border p-3"><div className="flex items-center justify-between"><span className="font-bold">{stageLabels[String(item.requested_outcome)]}</span><StatusBadge status={String(item.status)} /></div><p className="mt-2 text-xs text-muted-foreground">{String(item.request_note || "No request note")}</p>{permissions?.can_review_approval && item.status === "requested" ? <div className="mt-3 flex flex-wrap gap-2"><button className={buttonClass} onClick={() => submit(`/approval-requests/${String(item.id)}/review`, { status: "approved", review_comment: "Approved" })}>Approve</button><button className={secondaryButtonClass} onClick={() => submit(`/approval-requests/${String(item.id)}/review`, { status: "returned", review_comment: "Returned for clarification" })}>Return</button></div> : null}</article>)}{!(candidate.approvals || []).length ? <EmptyLine>No approval requests.</EmptyLine> : null}</div>
          <div className="space-y-2"><h3 className="text-sm font-black">Final decisions</h3>{(candidate.decisions || []).map((item) => <article key={Number(item.id)} className="rounded-lg border border-border p-3"><div className="flex items-center justify-between"><span className="font-bold">{stageLabels[String(item.decision)]}</span><span className="text-xs text-muted-foreground">{dateLabel(item.created_at)}</span></div><p className="mt-2 text-xs text-muted-foreground">{humanize(item.rejection_reason) || String(item.reason_detail || "No reason")}</p></article>)}{!(candidate.decisions || []).length ? <EmptyLine>No final decision.</EmptyLine> : null}</div>
        </div>
        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          {permissions?.can_request_approval ? <SimpleForm title="Request hiring approval" submitLabel="Request Academic Director approval" pending={mutation.isPending} onSubmit={(values) => submit("/approval-requests", values)} fields={<><label className="text-xs font-bold">Requested outcome<select name="requested_outcome" className={`${fieldClass} mt-1`}><option value="teacher_academy">Teacher Academy</option><option value="active_teacher">Active Teacher</option></select></label><label className="text-xs font-bold">Request note<textarea name="request_note" className={`${fieldClass} mt-1`} /></label></>} /> : null}
          {(permissions?.can_finalize || role === "hr_manager") ? <SimpleForm title="Record outcome" submitLabel="Record decision" pending={mutation.isPending} onSubmit={(values) => submit("/final-decisions", { ...values, approval_id: values.approval_id ? Number(values.approval_id) : null })} fields={<><label className="text-xs font-bold">Decision<select name="decision" className={`${fieldClass} mt-1`}><option value="on_hold">On Hold</option><option value="candidate_withdrew">Candidate Withdrew</option>{permissions?.can_finalize ? <><option value="rejected">Rejected</option><option value="teacher_academy">Teacher Academy</option><option value="active_teacher">Active Teacher</option></> : null}</select></label>{permissions?.can_finalize ? <label className="text-xs font-bold">Approved request<select name="approval_id" className={`${fieldClass} mt-1`}><option value="">Not required / select for hire</option>{approved.map((item) => <option key={Number(item.id)} value={Number(item.id)}>#{String(item.id)} · {stageLabels[String(item.requested_outcome)]}</option>)}</select></label> : null}<label className="text-xs font-bold">Rejection reason<select name="rejection_reason" className={`${fieldClass} mt-1`}><option value="">Not applicable</option>{options.data?.rejection_reasons.map((reason) => <option key={reason} value={reason}>{humanize(reason)}</option>)}</select></label><label className="text-xs font-bold">Reason / explanation<textarea name="reason_detail" className={`${fieldClass} mt-1`} /></label><label className="text-xs font-bold">Follow-up date<input name="follow_up_at" type="datetime-local" className={`${fieldClass} mt-1`} /></label></>} /> : null}
        </div>
        {pendingApprovals.length ? <p className="mt-3 text-xs text-muted-foreground">Hiring cannot be finalized until an assigned Academic Director approves the matching outcome.</p> : null}
      </Section>

      <Section id="tasks" title="Tasks" icon={<CalendarClock className="h-4 w-4" />}>
        <div className="space-y-2">{(candidate.tasks || []).map((task) => <article key={task.id} className="flex min-h-14 flex-wrap items-center justify-between gap-3 rounded-lg border border-border p-3"><div><p className="font-bold">{task.title}</p><p className="text-xs text-muted-foreground">{dateLabel(task.due_at)}</p></div><StatusBadge status={task.effective_status} /></article>)}{!(candidate.tasks || []).length ? <EmptyLine>No tasks.</EmptyLine> : null}</div>
        {permissions?.can_manage_tasks ? <div className="mt-4"><SimpleForm title="Add task" submitLabel="Create task" pending={mutation.isPending} onSubmit={(values, form) => { submit("/tasks", values); form.reset(); }} fields={<><label className="text-xs font-bold">Title<input required name="title" className={`${fieldClass} mt-1`} /></label><label className="text-xs font-bold">Due date<input name="due_at" type="datetime-local" className={`${fieldClass} mt-1`} /></label><label className="text-xs font-bold">Note<textarea name="note" className={`${fieldClass} mt-1`} /></label><input type="hidden" name="status" value="pending" /></>} /></div> : null}
      </Section>

      <Section id="notes" title="Notes" icon={<MessageSquareText className="h-4 w-4" />}>
        <div className="space-y-2">{(candidate.notes || []).map((note) => <article key={Number(note.id)} className="rounded-lg border border-border p-3"><p className="whitespace-pre-wrap text-sm">{String(note.body)}</p><p className="mt-2 text-xs text-muted-foreground">{String(note.author || "Unknown actor")} · {dateLabel(note.created_at)}</p></article>)}{!(candidate.notes || []).length ? <EmptyLine>No notes.</EmptyLine> : null}</div>
        {permissions?.can_add_note ? <form className="mt-4 flex flex-col gap-2 sm:flex-row" onSubmit={(event) => { event.preventDefault(); const values = formValues(event.currentTarget); submit("/notes", values); event.currentTarget.reset(); }}><label className="sr-only" htmlFor="candidate-note">Add note</label><textarea id="candidate-note" required name="body" placeholder="Add an actor-attributed note" className={`${fieldClass} flex-1`} /><button className={buttonClass} disabled={mutation.isPending}>Add note</button></form> : null}
      </Section>

      <Section id="activity" title="Activity" icon={<Activity className="h-4 w-4" />}>
        <ol className="space-y-3">{(candidate.activity || []).map((item) => <li key={Number(item.id)} className="border-l-2 border-primary/30 pl-4"><p className="text-sm font-bold">{humanize(item.event_type)}</p><p className="mt-1 text-xs text-muted-foreground">{String(item.actor || "System")} · {dateLabel(item.created_at)}</p></li>)}{!(candidate.activity || []).length ? <EmptyLine>No activity yet.</EmptyLine> : null}</ol>
      </Section>
    </div>
  );
}

function NewCandidateModal({ open, onClose, onCreated, options }: { open: boolean; onClose: () => void; onCreated: (message: string) => void; options?: RecruitmentOptions }) {
  const queryClient = useQueryClient();
  const create = useMutation({ mutationFn: (values: Record<string, string | number | null>) => recruitmentRequest<MutationPayload>(`${API}/candidates`, { method: "POST", body: jsonBody(values) }), onSuccess: (result) => { onCreated(result.message); onClose(); void queryClient.invalidateQueries({ queryKey: ["recruitment"] }); }, onError: (error) => onCreated(queryError(error)) });
  return <Modal open={open} onClose={onClose} title="Add candidate" subtitle="Only the name is required; missing fields never block stage movement." size="md"><form onSubmit={(event) => { event.preventDefault(); create.mutate(formValues(event.currentTarget)); }}><ModalBody className="grid gap-3"><label className="text-xs font-bold">Full name<input autoFocus required name="full_name" className={`${fieldClass} mt-1`} /></label><label className="text-xs font-bold">Phone<input name="phone" className={`${fieldClass} mt-1`} /></label><label className="text-xs font-bold">Applied position<input name="applied_position" className={`${fieldClass} mt-1`} /></label><label className="text-xs font-bold">Application date<input name="application_date" type="date" className={`${fieldClass} mt-1`} /></label><label className="text-xs font-bold">Source<select name="source" className={`${fieldClass} mt-1`}><option value="">Not set</option>{options?.sources.map((source) => <option key={source}>{source}</option>)}</select></label><label className="text-xs font-bold">Initial note<textarea name="comment" className={`${fieldClass} mt-1`} /></label></ModalBody><ModalFooter><div className="flex justify-end gap-2"><button className={secondaryButtonClass} type="button" onClick={onClose}>Cancel</button><button className={buttonClass} disabled={create.isPending} type="submit">{create.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}Create candidate</button></div></ModalFooter></form></Modal>;
}

export default function RecruitmentWorkspace({ authLogin = "", authRole = "", role = "hr_manager", view = "pipeline", basePath = "/hr-manager", candidateId = null, csrfToken = "" }: Props) {
  const [announcement, setAnnouncement] = useState("");
  const [newCandidateOpen, setNewCandidateOpen] = useState(false);
  const options = useQuery({ queryKey: ["recruitment", "options"], queryFn: () => recruitmentRequest<RecruitmentOptions>(`${API}/options`) });
  const effectiveRole = role || (authRole as RecruitmentRole);
  const active = view === "candidate" ? "candidates" : view;
  const navItems = useMemo(() => [
    { key: "pipeline", label: "Pipeline", href: `${basePath}/pipeline`, icon: KanbanSquare },
    { key: "candidates", label: "Candidates", href: `${basePath}/candidates`, icon: UsersRound },
    { key: "tasks", label: "Tasks", href: `${basePath}/tasks`, icon: CalendarClock },
    { key: "profile", label: "Profile", href: `${basePath}/profile`, icon: UserRound },
  ], [basePath]);
  const title = { pipeline: "Recruitment Pipeline", candidates: "Candidates", tasks: "Recruitment Tasks", candidate: "Candidate Profile", profile: "Profile" }[view];

  return (
    <RoleWorkspaceShell
      authLogin={authLogin}
      csrfToken={csrfToken}
      active={active}
      homeHref={workspaceHome(effectiveRole)}
      navItems={navItems}
      roleLabel={roleLabel(effectiveRole)}
      sectionLabel="Recruitment"
      workspaceLabel="Teacher Recruitment"
      mobileNavigationMode="drawer"
      maxWidthClass="max-w-[1600px]"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div><p className="text-xs font-black uppercase tracking-[0.16em] text-primary">Teacher Recruitment</p><h1 className="mt-1 text-2xl font-black tracking-tight sm:text-3xl">{title}</h1><p className="mt-1 max-w-2xl text-sm text-muted-foreground">Manual, auditable recruitment workflow with assigned academic evaluation and protected hiring approval.</p></div>
        {effectiveRole === "hr_manager" && view !== "profile" ? <button className={buttonClass} onClick={() => setNewCandidateOpen(true)}><Plus className="h-4 w-4" />Add candidate</button> : null}
      </div>
      <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">{announcement}</div>
      {announcement ? <div className="flex min-h-11 items-center justify-between gap-3 rounded-lg border border-primary/20 bg-primary/5 px-3 text-sm" role="alert"><span>{announcement}</span><button className="min-h-11 px-2 font-bold" onClick={() => setAnnouncement("")}>Dismiss</button></div> : null}

      {view === "pipeline" ? <PipelineView basePath={basePath} onAnnouncement={setAnnouncement} /> : null}
      {view === "candidates" ? <CandidateListView basePath={basePath} /> : null}
      {view === "tasks" ? <TasksView basePath={basePath} /> : null}
      {view === "candidate" && Number(candidateId) > 0 ? <CandidateProfile candidateId={Number(candidateId)} basePath={basePath} role={effectiveRole} onAnnouncement={setAnnouncement} /> : null}
      {view === "profile" ? <section className="rounded-xl border border-border bg-card p-5"><div className="flex items-center gap-3"><div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary"><BriefcaseBusiness className="h-6 w-6" /></div><div><h2 className="font-black">{authLogin || roleLabel(effectiveRole)}</h2><p className="text-sm text-muted-foreground">{roleLabel(effectiveRole)} recruitment access</p></div></div><div className="mt-5 flex flex-wrap gap-2"><a className={secondaryButtonClass} href={workspaceHome(effectiveRole)}>Back to main workspace</a><a className={secondaryButtonClass} href="/account/security">Account security</a></div></section> : null}

      <NewCandidateModal open={newCandidateOpen} onClose={() => setNewCandidateOpen(false)} onCreated={setAnnouncement} options={options.data} />
    </RoleWorkspaceShell>
  );
}
