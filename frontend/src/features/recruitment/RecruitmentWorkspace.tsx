import { BriefcaseBusiness, CalendarClock, KanbanSquare, Loader2, Plus, Settings2, ShieldCheck, UsersRound } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { CandidateListView } from "@/features/recruitment/CandidateListView";
import { CandidateProfile } from "@/features/recruitment/CandidateProfile";
import { DecisionQueueView } from "@/features/recruitment/DecisionQueueView";
import { PipelineView } from "@/features/recruitment/PipelineView";
import { SettingsView } from "@/features/recruitment/SettingsView";
import { TasksView } from "@/features/recruitment/TasksView";
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
  const create = useMutation({
    mutationFn: (values: Record<string, string | number | null>) => recruitmentRequest<MutationPayload>(`${RECRUITMENT_API}/candidates`, { method: "POST", body: jsonBody(values) }),
    onSuccess: (result) => {
      onCreated(result.message);
      onClose();
      void queryClient.invalidateQueries({ queryKey: ["recruitment"] });
    },
    onError: (error) => onCreated(queryError(error), "error"),
  });
  return (
    <Modal open={open} onClose={onClose} title="Add candidate" subtitle="Only the name is required; missing fields never block stage movement." size="md">
      <form onSubmit={(event) => { event.preventDefault(); create.mutate(formValues(event.currentTarget)); }}>
        <ModalBody className="grid gap-3">
          {create.error ? <div role="alert" className="rounded-lg border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive">{queryError(create.error)}</div> : null}
          <label className="text-xs font-semibold">Full name<input autoFocus required name="full_name" className={`${fieldClass} mt-1`} /></label>
          <label className="text-xs font-semibold">Phone<input name="phone" type="tel" className={`${fieldClass} mt-1`} /></label>
          <label className="text-xs font-semibold">Applied position<input name="applied_position" className={`${fieldClass} mt-1`} /></label>
          <label className="text-xs font-semibold">Application date<input name="application_date" type="date" className={`${fieldClass} mt-1`} /></label>
          <label className="text-xs font-semibold">Source<select name="source" className={`${fieldClass} mt-1`}><option value="">Not set</option>{options?.sources.map((source) => <option key={source}>{source}</option>)}</select></label>
          <label className="text-xs font-semibold">Initial note<textarea name="comment" className={`${fieldClass} mt-1 min-h-24`} /></label>
        </ModalBody>
        <ModalFooter><div className="flex justify-end gap-2"><button className={secondaryButtonClass} type="button" onClick={onClose}>Cancel</button><button className={buttonClass} disabled={create.isPending} type="submit">{create.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}Create candidate</button></div></ModalFooter>
      </form>
    </Modal>
  );
}

export default function RecruitmentWorkspace({ authLogin = "", authRole = "", role = "hr_manager", view = "pipeline", basePath = "/hr-manager", candidateId = null, csrfToken = "" }: Props) {
  const [newCandidateOpen, setNewCandidateOpen] = useState(false);
  const { toast, showToast, clearToast } = useFloatingToast();
  const options = useQuery({ queryKey: ["recruitment", "options"], queryFn: () => recruitmentRequest<RecruitmentOptions>(`${RECRUITMENT_API}/options`) });
  const effectiveRole = role || (authRole as RecruitmentRole);
  const active = view === "candidate" ? "candidates" : view === "profile" ? "profile" : view;
  const navItems = useMemo(() => {
    if (effectiveRole === "academic_director") return [
        { key: "decisions", label: "Decisions", href: `${basePath}/decisions`, icon: ShieldCheck },
        { key: "candidates", label: "Candidates", href: `${basePath}/candidates`, icon: UsersRound },
        { key: "tasks", label: "Tasks", href: `${basePath}/tasks`, icon: CalendarClock },
      ];
    const items = [
      { key: "pipeline", label: "Pipeline", href: `${basePath}/pipeline`, icon: KanbanSquare },
      { key: "candidates", label: "Candidates", href: `${basePath}/candidates`, icon: UsersRound },
      { key: "tasks", label: "Tasks", href: `${basePath}/tasks`, icon: CalendarClock },
    ];
    if (effectiveRole === "hr_manager") items.push({ key: "settings", label: "Settings", href: `${basePath}/settings`, icon: Settings2 });
    return items;
  }, [basePath, effectiveRole]);
  const title = { pipeline: "Recruitment Pipeline", decisions: "Hiring Decisions", candidates: "Candidates", tasks: "Recruitment Tasks", settings: "Recruitment Settings", candidate: "Candidate Profile", profile: "Profile" }[view];
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
            {view === "pipeline" ? <p className="mt-0.5 hidden max-w-2xl text-[13px] text-muted-foreground sm:block">Move candidates through a manual, auditable hiring workflow.</p> : null}
            {view === "decisions" ? <p className="mt-0.5 hidden max-w-2xl text-[13px] text-muted-foreground sm:block">Review assigned evaluations and pending hiring requests.</p> : null}
          </div>
          {effectiveRole === "hr_manager" && !["profile", "settings"].includes(view) ? <button className={buttonClass} onClick={() => setNewCandidateOpen(true)}><Plus className="h-4 w-4" />Add candidate</button> : null}
        </header>
      ) : null}

      <FloatingToast toast={toast} onClose={clearToast} />

      {view === "pipeline" ? <PipelineView basePath={basePath} role={effectiveRole} options={options.data} onAnnouncement={showToast} /> : null}
      {view === "decisions" ? <DecisionQueueView basePath={basePath} /> : null}
      {view === "candidates" ? <CandidateListView basePath={basePath} /> : null}
      {view === "tasks" ? <TasksView basePath={basePath} /> : null}
      {view === "settings" && effectiveRole === "hr_manager" ? <SettingsView onAnnouncement={showToast} /> : null}
      {view === "candidate" && Number(candidateId) > 0 ? <CandidateProfile candidateId={Number(candidateId)} basePath={basePath} role={effectiveRole} onAnnouncement={showToast} /> : null}
      {view === "profile" ? <section className="rounded-xl border border-border bg-card p-4"><div className="flex items-center gap-3"><div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary"><BriefcaseBusiness className="h-5 w-5" /></div><div><h2 className="text-sm font-semibold">{authLogin || roleLabel(effectiveRole)}</h2><p className="text-xs text-muted-foreground">{roleLabel(effectiveRole)} recruitment access</p></div></div><div className="mt-4 flex flex-wrap gap-2">{effectiveRole !== "hr_manager" ? <a className={secondaryButtonClass} href={home}>Back to main workspace</a> : null}<a className={secondaryButtonClass} href="/account/security">Account security</a></div></section> : null}

      <NewCandidateModal open={newCandidateOpen} onClose={() => setNewCandidateOpen(false)} onCreated={showToast} options={options.data} />
    </RoleWorkspaceShell>
  );
}
