import { Ban, BarChart3, BriefcaseBusiness, CalendarClock, CalendarDays, KanbanSquare, Loader2, Plus, Settings2, ShieldCheck, Trash2, UsersRound } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { CandidateListView } from "@/features/recruitment/CandidateListView";
import { AnalyticsView } from "@/features/recruitment/AnalyticsView";
import { CandidateProfile } from "@/features/recruitment/CandidateProfile";
import { DecisionQueueView } from "@/features/recruitment/DecisionQueueView";
import { PipelineView } from "@/features/recruitment/PipelineView";
import { RejectedCandidatesView } from "@/features/recruitment/RejectedCandidatesView";
import { ScheduleView } from "@/features/recruitment/ScheduleView";
import { SettingsView } from "@/features/recruitment/SettingsView";
import { TasksView } from "@/features/recruitment/TasksView";
import { TrashBinView } from "@/features/recruitment/TrashBinView";
import { TeachersView } from "@/features/recruitment/TeachersView";
import { TelegramConnectionCard } from "@/features/recruitment/TelegramConnectionCard";
import { formValues, jsonBody, recruitmentRequest } from "@/features/recruitment/api";
import { type RecruitmentCandidate, type RecruitmentOptions, type RecruitmentRole, type RecruitmentView } from "@/features/recruitment/model";
import {
  RECRUITMENT_API,
  buttonClass,
  fieldClass,
  queryError,
  roleLabel,
  secondaryButtonClass,
  workspaceHome,
} from "@/features/recruitment/ui";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";
import { FloatingToast, type FloatingToastTone, useFloatingToast } from "@/shared/ui/FloatingToast";
import { RoleWorkspaceShell } from "@/shared/ui/RoleWorkspaceShell";

type Props = {
  authLogin?: string;
  authRole?: string;
  role?: RecruitmentRole;
  view?: RecruitmentView;
  basePath?: string;
  candidateId?: number | string | null;
  csrfToken?: string;
};

type MutationPayload = { message: string; candidate?: RecruitmentCandidate };

function NewCandidateModal({ open, onClose, onCreated, options }: { open: boolean; onClose: () => void; onCreated: (message: string, tone?: FloatingToastTone) => void; options?: RecruitmentOptions }) {
  const queryClient = useQueryClient();
  const [sourceId, setSourceId] = useState("");
  const [subsourceId, setSubsourceId] = useState("");
  const [dirty, setDirty] = useState(false);
  const create = useMutation({
    mutationFn: (values: Record<string, string | number | null>) => recruitmentRequest<MutationPayload>(`${RECRUITMENT_API}/candidates`, { method: "POST", body: jsonBody(values) }),
    onSuccess: (result) => {
      onCreated(result.message);
      setSourceId("");
      setSubsourceId("");
      setDirty(false);
      onClose();
      void queryClient.invalidateQueries({ queryKey: ["recruitment"] });
    },
    onError: (error) => onCreated(queryError(error), "error"),
  });
  const close = () => {
    if (create.isPending) return;
    if (dirty && !window.confirm("Discard the candidate details you entered?")) return;
    setSourceId("");
    setSubsourceId("");
    setDirty(false);
    onClose();
  };
  return (
    <Modal open={open} onClose={close} title="Add candidate" size="lg" mobileMode="sheet" closeOnEscape={!create.isPending} closeOnOutsideClick={!create.isPending}>
      <form className="flex min-h-0 flex-1 flex-col" onChange={() => setDirty(true)} onSubmit={(event) => { event.preventDefault(); create.mutate(formValues(event.currentTarget)); }}>
        <ModalBody className="grid content-start gap-3 md:grid-cols-2 lg:grid-cols-3">
          {create.error ? <div role="alert" className="rounded-lg border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive md:col-span-2 lg:col-span-3">{queryError(create.error)}</div> : null}
          <label className="text-xs font-semibold lg:col-span-2">Full name<input autoFocus required name="full_name" className={`${fieldClass} mt-1`} /></label>
          <label className="text-xs font-semibold">Phone<input name="phone" type="tel" className={`${fieldClass} mt-1`} /></label>
          <label className="text-xs font-semibold">Applied position<input name="applied_position" className={`${fieldClass} mt-1`} /></label>
          <label className="text-xs font-semibold">Subject<select name="subject_id" className={`${fieldClass} mt-1`}><option value="">Not set</option>{options?.subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}</select></label>
          <label className="text-xs font-semibold">Application date<input name="application_date" type="date" defaultValue={new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Tashkent" }).format(new Date())} className={`${fieldClass} mt-1`} /></label>
          <label className="text-xs font-semibold">Source<select name="source_option_id" value={sourceId} onChange={(event) => { setSourceId(event.target.value); setSubsourceId(""); }} className={`${fieldClass} mt-1`}><option value="">Not set</option>{options?.sources.map((source) => <option key={source.id} value={source.id}>{source.label}</option>)}</select></label>
          <label className="text-xs font-semibold md:col-span-1 lg:col-span-2">Subsource<select name="subsource_option_id" value={subsourceId} onChange={(event) => setSubsourceId(event.target.value)} disabled={!sourceId} required={Boolean(sourceId && options?.subsources.some((item) => String(item.parent_id || "") === sourceId))} className={`${fieldClass} mt-1 disabled:cursor-not-allowed disabled:opacity-60`}><option value="">{sourceId ? "Select subsource" : "Select a source first"}</option>{options?.subsources.filter((item) => String(item.parent_id || "") === sourceId).map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
        </ModalBody>
        <ModalFooter><div className="flex justify-end gap-2"><button className={secondaryButtonClass} type="button" disabled={create.isPending} onClick={close}>Cancel</button><button className={buttonClass} disabled={create.isPending} type="submit">{create.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}Create candidate</button></div></ModalFooter>
      </form>
    </Modal>
  );
}

export default function RecruitmentWorkspace({ authLogin = "", authRole = "", role = "hr_manager", view = "pipeline", basePath = "/hr-manager", candidateId = null, csrfToken = "" }: Props) {
  const [newCandidateOpen, setNewCandidateOpen] = useState(false);
  const { toast, showToast, clearToast } = useFloatingToast();
  const options = useQuery({ queryKey: ["recruitment", "options"], queryFn: () => recruitmentRequest<RecruitmentOptions>(`${RECRUITMENT_API}/options`) });
  const effectiveRole = role || (authRole as RecruitmentRole);
  const active = view === "candidate" ? (effectiveRole === "hr_manager" ? "pipeline" : "candidates") : view === "profile" ? "profile" : view;
  const navItems = useMemo(() => {
    if (effectiveRole === "academic_director") return [
        { key: "decisions", label: "Decisions", href: `${basePath}/decisions`, icon: ShieldCheck },
        { key: "candidates", label: "Candidates", href: `${basePath}/candidates`, icon: UsersRound },
        { key: "schedule", label: "Schedule", href: `${basePath}/schedule`, icon: CalendarDays },
      ];
    if (effectiveRole === "head_of_department") return [
      { key: "candidates", label: "Assigned Candidates", href: `${basePath}/candidates`, icon: UsersRound },
      { key: "schedule", label: "Assigned Schedule", href: `${basePath}/schedule`, icon: CalendarDays },
    ];
    if (effectiveRole === "hr_manager") return [
      { key: "pipeline", label: "Pipeline", href: `${basePath}/pipeline`, icon: KanbanSquare },
      { key: "teachers", label: "Teachers", href: `${basePath}/teachers`, icon: UsersRound },
      { key: "analytics", label: "Analytics", href: `${basePath}/analytics`, icon: BarChart3 },
      { key: "schedule", label: "Schedule", href: `${basePath}/schedule`, icon: CalendarDays },
      { key: "rejected", label: "Rejected", href: `${basePath}/rejected`, icon: Ban },
      { key: "trash", label: "Trash Bin", href: `${basePath}/trash`, icon: Trash2 },
      { key: "settings", label: "Settings", href: `${basePath}/settings`, icon: Settings2 },
    ];
    const items = [
      { key: "pipeline", label: "Pipeline", href: `${basePath}/pipeline`, icon: KanbanSquare },
      ...(effectiveRole === "ceo" ? [{ key: "analytics", label: "Analytics", href: `${basePath}/analytics`, icon: BarChart3 }] : []),
      { key: "candidates", label: "Candidates", href: `${basePath}/candidates`, icon: UsersRound },
      { key: "schedule", label: "Schedule", href: `${basePath}/schedule`, icon: CalendarDays },
      { key: "tasks", label: "Tasks", href: `${basePath}/tasks`, icon: CalendarClock },
      ...(effectiveRole === "ceo" ? [{ key: "settings", label: "SLA Settings", href: `${basePath}/settings`, icon: Settings2 }] : []),
    ];
    return items;
  }, [basePath, effectiveRole]);
  const title = { pipeline: "Recruitment Pipeline", teachers: "Teachers", analytics: "Recruitment Analytics", decisions: "Hiring Decisions", candidates: "Candidates", schedule: "Interview & Demo Schedule", tasks: "Recruitment Tasks", rejected: "Closed Candidates", settings: "Recruitment Settings", trash: "Trash Bin", candidate: "Candidate Profile", profile: "Profile" }[view];
  const home = workspaceHome(effectiveRole);
  const workspaceBackLink = effectiveRole === "hr_manager" ? undefined : { href: home, label: `Back to ${roleLabel(effectiveRole)} workspace` };

  return (
    <RoleWorkspaceShell
      authLogin={authLogin}
      csrfToken={csrfToken}
      active={active}
      homeHref={home}
      navItems={navItems}
      roleLabel={roleLabel(effectiveRole)}
      sectionLabel="Recruitment"
      workspaceLabel="Teacher Recruitment"
      mobileNavigationMode="drawer"
      desktopSidebarMode="collapsible"
      desktopSidebarInitialState="adaptive"
      desktopSidebarStorageKey="msi:recruitment:sidebar:v1"
      workspaceBackLink={workspaceBackLink}
      profileHref={`${basePath}/profile`}
      maxWidthClass="max-w-[1600px]"
      sectionClassName="gap-3"
    >
      {view !== "candidate" ? (
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">Teacher Recruitment</p>
            <h1 className="mt-0.5 text-xl font-bold tracking-tight sm:text-2xl">{title}</h1>
            {view === "decisions" ? <p className="mt-0.5 hidden max-w-2xl text-[13px] text-muted-foreground sm:block">Review assigned evaluations and pending hiring requests.</p> : null}
            {view === "schedule" ? <p className="mt-0.5 hidden max-w-2xl text-[13px] text-muted-foreground sm:block">Manage upcoming job interviews and demo lessons in Asia/Tashkent time.</p> : null}
            {view === "trash" ? <p className="mt-0.5 hidden max-w-2xl text-[13px] text-muted-foreground sm:block">Deleted candidates only. Open a profile to restore one.</p> : null}
          </div>
        </header>
      ) : null}

      <FloatingToast toast={toast} onClose={clearToast} />

      {view === "pipeline" ? <PipelineView basePath={basePath} options={options.data} canAddCandidate={effectiveRole === "hr_manager"} onAddCandidate={() => setNewCandidateOpen(true)} onAnnouncement={showToast} /> : null}
      {view === "teachers" && effectiveRole === "hr_manager" ? <TeachersView basePath={basePath} /> : null}
      {view === "analytics" && ["hr_manager", "ceo"].includes(effectiveRole) ? <AnalyticsView basePath={basePath} /> : null}
      {view === "decisions" ? <DecisionQueueView basePath={basePath} /> : null}
      {view === "candidates" ? <CandidateListView basePath={basePath} /> : null}
      {view === "schedule" ? <ScheduleView basePath={basePath} role={effectiveRole} options={options.data} onAnnouncement={showToast} /> : null}
      {view === "tasks" ? <TasksView basePath={basePath} /> : null}
      {view === "rejected" && effectiveRole === "hr_manager" ? <RejectedCandidatesView basePath={basePath} /> : null}
      {view === "settings" && ["hr_manager", "ceo"].includes(effectiveRole) ? <SettingsView onAnnouncement={showToast} /> : null}
      {view === "trash" && effectiveRole === "hr_manager" ? <TrashBinView basePath={basePath} /> : null}
      {view === "candidate" && Number(candidateId) > 0 ? <CandidateProfile candidateId={Number(candidateId)} basePath={basePath} role={effectiveRole} onAnnouncement={showToast} /> : null}
      {view === "profile" ? <div className="space-y-3"><section className="rounded-xl border border-border bg-card p-4"><div className="flex items-center gap-3"><div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary"><BriefcaseBusiness className="h-5 w-5" /></div><div><h2 className="text-sm font-semibold">{authLogin || roleLabel(effectiveRole)}</h2><p className="text-xs text-muted-foreground">{roleLabel(effectiveRole)} recruitment access</p></div></div><div className="mt-4 flex flex-wrap gap-2">{effectiveRole !== "hr_manager" ? <a className={secondaryButtonClass} href={home}>Back to main workspace</a> : null}<a className={secondaryButtonClass} href="/account/security">Account security</a></div></section>{["hr_manager", "academic_director", "head_of_department"].includes(effectiveRole) ? <TelegramConnectionCard /> : null}</div> : null}

      <NewCandidateModal open={newCandidateOpen} onClose={() => setNewCandidateOpen(false)} onCreated={showToast} options={options.data} />
    </RoleWorkspaceShell>
  );
}
