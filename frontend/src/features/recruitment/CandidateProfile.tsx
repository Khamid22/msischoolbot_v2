import {
  Activity,
  ArrowLeft,
  BriefcaseBusiness,
  CalendarClock,
  ClipboardCheck,
  FileText,
  Loader2,
  MessageSquareText,
  Pencil,
  Plus,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useState, type FormEvent, type KeyboardEvent, type ReactNode } from "react";

import { formValues, jsonBody, recruitmentRequest } from "@/features/recruitment/api";
import { dateLabel, humanize, manualStages, stageLabels, type RecruitmentCandidate, type RecruitmentOptions } from "@/features/recruitment/model";
import {
  RECRUITMENT_API,
  DefinitionGrid,
  EmptyLine,
  PageState,
  buttonClass,
  fieldClass,
  queryError,
  secondaryButtonClass,
} from "@/features/recruitment/ui";
import { ActionMenu, type ActionMenuItem } from "@/shared/ui/ActionMenu";
import { ConfirmDialog } from "@/shared/ui/ConfirmDialog";
import { Drawer } from "@/shared/ui/Drawer";
import { StatusBadge } from "@/shared/ui/StatusBadge";

type ProfileTab = "overview" | "evaluations" | "documents" | "hiring" | "activity";
type ProfileAction =
  | { kind: "edit_profile" }
  | { kind: "move_candidate" }
  | { kind: "upload_document"; document?: Record<string, unknown> }
  | { kind: "record_interview" }
  | { kind: "record_test" }
  | { kind: "record_demo" }
  | { kind: "assign_evaluators" }
  | { kind: "request_approval" }
  | { kind: "record_outcome" }
  | { kind: "review_approval"; approval: Record<string, unknown>; status: "approved" | "returned" }
  | { kind: "add_task" }
  | { kind: "add_note" };

type MutationPayload = { message: string; candidate?: RecruitmentCandidate };
const profileTabs: Array<{ key: ProfileTab; label: string }> = [
  { key: "overview", label: "Overview" },
  { key: "evaluations", label: "Evaluations" },
  { key: "documents", label: "Documents" },
  { key: "hiring", label: "Hiring" },
  { key: "activity", label: "Activity" },
];

function text(value: unknown) {
  return String(value ?? "");
}

function Panel({ title, icon, action, children }: { title: string; icon: ReactNode; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-border bg-card shadow-sm">
      <div className="flex min-h-12 items-center justify-between gap-3 border-b border-border px-3 py-2">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-foreground">{icon}{title}</h2>
        {action}
      </div>
      <div className="p-3">{children}</div>
    </section>
  );
}

function AttemptList({ items, empty }: { items: Array<Record<string, unknown>>; empty: string }) {
  if (!items.length) return <EmptyLine>{empty}</EmptyLine>;
  return (
    <div className="space-y-2">
      {items.map((item, index) => (
        <article key={Number(item.id || index)} className="rounded-lg border border-border p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <StatusBadge status={text(item.result || "recorded")} />
            <span className="text-xs text-muted-foreground">{dateLabel(item.interview_at || item.test_at || item.demo_at || item.created_at)}</span>
          </div>
          {item.score !== null && item.score !== undefined ? (
            <p className="mt-2 text-[13px] font-semibold">Score: {text(item.score)}{item.maximum_score ? ` / ${text(item.maximum_score)} (${text(item.percentage || 0)}%)` : " / 10"}</p>
          ) : null}
          <p className="mt-1.5 whitespace-pre-wrap text-[13px] leading-5 text-muted-foreground">{text(item.notes || item.overview || item.recommendation || "No notes")}</p>
        </article>
      ))}
    </div>
  );
}

function OutcomeFields({ candidate, options }: { candidate: RecruitmentCandidate; options?: RecruitmentOptions }) {
  const canFinalize = Boolean(candidate.permissions?.can_finalize);
  const canReject = Boolean(candidate.permissions?.can_reject);
  const availableDecisions = canFinalize
    ? ["on_hold", "candidate_withdrew", "rejected", "teacher_academy", "active_teacher"]
    : canReject
      ? ["rejected"]
      : ["on_hold", "candidate_withdrew"];
  const [decision, setDecision] = useState(availableDecisions[0]);
  const [rejectionReason, setRejectionReason] = useState("");
  const approved = (candidate.approvals || []).filter((item) => item.status === "approved");
  const isHire = decision === "teacher_academy" || decision === "active_teacher";
  return (
    <>
      <label className="text-xs font-semibold">Decision<select name="decision" value={decision} onChange={(event) => setDecision(event.target.value)} className={`${fieldClass} mt-1`}>{availableDecisions.map((value) => <option key={value} value={value}>{stageLabels[value]}</option>)}</select></label>
      {isHire ? <label className="text-xs font-semibold">Approved request<select required name="approval_id" className={`${fieldClass} mt-1`}><option value="">Select an approved request</option>{approved.filter((item) => item.requested_outcome === decision).map((item) => <option key={Number(item.id)} value={Number(item.id)}>#{text(item.id)} · {stageLabels[text(item.requested_outcome)]}</option>)}</select></label> : null}
      {decision === "rejected" ? <label className="text-xs font-semibold">Rejection reason<select required name="rejection_reason" value={rejectionReason} onChange={(event) => setRejectionReason(event.target.value)} className={`${fieldClass} mt-1`}><option value="">Select a reason</option>{options?.rejection_reasons.map((reason) => <option key={reason} value={reason}>{humanize(reason)}</option>)}</select></label> : null}
      {["rejected", "on_hold", "candidate_withdrew"].includes(decision) ? <label className="text-xs font-semibold">Reason / explanation<textarea name="reason_detail" required={decision === "on_hold" || rejectionReason === "other"} className={`${fieldClass} mt-1 min-h-24`} /></label> : null}
      {decision === "on_hold" ? <label className="text-xs font-semibold">Follow-up date<input name="follow_up_at" type="datetime-local" className={`${fieldClass} mt-1`} /></label> : null}
    </>
  );
}

function ActionFields({ action, candidate, options }: { action: ProfileAction; candidate: RecruitmentCandidate; options?: RecruitmentOptions }) {
  switch (action.kind) {
    case "edit_profile":
      return <div className="grid gap-3 sm:grid-cols-2"><label className="text-xs font-semibold">Full name<input name="full_name" defaultValue={candidate.full_name} required className={`${fieldClass} mt-1`} /></label><label className="text-xs font-semibold">Phone<input name="phone" type="tel" defaultValue={candidate.phone} className={`${fieldClass} mt-1`} /></label><label className="text-xs font-semibold">Telegram<input name="telegram_username" defaultValue={candidate.telegram_username} className={`${fieldClass} mt-1`} /></label><label className="text-xs font-semibold">Position<input name="applied_position" defaultValue={candidate.applied_position} className={`${fieldClass} mt-1`} /></label><label className="text-xs font-semibold">Application date<input name="application_date" type="date" defaultValue={candidate.application_date?.slice(0, 10)} className={`${fieldClass} mt-1`} /></label><label className="text-xs font-semibold">Source<select name="source" defaultValue={candidate.source} className={`${fieldClass} mt-1`}><option value="">Not set</option>{options?.sources.map((source) => <option key={source}>{source}</option>)}</select></label><label className="text-xs font-semibold">Age<input name="age" type="number" min="14" max="100" defaultValue={candidate.age || ""} className={`${fieldClass} mt-1`} /></label><label className="text-xs font-semibold">English level<input name="english_level" defaultValue={candidate.english_level} className={`${fieldClass} mt-1`} /></label><label className="text-xs font-semibold">Preferred schedule<input name="preferred_schedule" defaultValue={candidate.preferred_schedule} className={`${fieldClass} mt-1`} /></label><label className="text-xs font-semibold">Availability<input name="employment_availability" defaultValue={candidate.employment_availability} className={`${fieldClass} mt-1`} /></label><label className="text-xs font-semibold">Available start date<input name="available_start_date" type="date" defaultValue={candidate.available_start_date?.slice(0, 10)} className={`${fieldClass} mt-1`} /></label><label className="text-xs font-semibold">Expected salary (UZS)<input name="expected_salary_uzs" type="number" min="0" defaultValue={candidate.expected_salary_uzs || ""} className={`${fieldClass} mt-1`} /></label><label className="text-xs font-semibold sm:col-span-2">Address<textarea name="address" defaultValue={candidate.address} className={`${fieldClass} mt-1 min-h-20`} /></label><label className="text-xs font-semibold sm:col-span-2">Work experience<textarea name="work_experience" defaultValue={candidate.work_experience} className={`${fieldClass} mt-1 min-h-20`} /></label><label className="text-xs font-semibold sm:col-span-2">Teaching experience<textarea name="teaching_experience" defaultValue={candidate.teaching_experience} className={`${fieldClass} mt-1 min-h-20`} /></label><label className="text-xs font-semibold sm:col-span-2">Motivation & expectations<textarea name="motivation_expectations" defaultValue={candidate.motivation_expectations} className={`${fieldClass} mt-1 min-h-20`} /></label><label className="text-xs font-semibold sm:col-span-2">Interests & hobbies<textarea name="interests_hobbies" defaultValue={candidate.interests_hobbies} className={`${fieldClass} mt-1 min-h-20`} /></label></div>;
    case "move_candidate":
      return <div className="grid gap-3"><label className="text-xs font-semibold">New stage<select required name="stage" className={`${fieldClass} mt-1`}><option value="">Choose a stage</option>{manualStages.filter((stage) => stage !== candidate.status).map((stage) => <option key={stage} value={stage}>{stageLabels[stage]}</option>)}</select></label><label className="text-xs font-semibold">Reason<textarea name="reason" defaultValue="Candidate profile move" className={`${fieldClass} mt-1 min-h-20`} /></label><p className="text-xs leading-5 text-muted-foreground">Academy, Active Teacher, rejection, hold, and withdrawal continue through the Hiring tab.</p></div>;
    case "upload_document":
      return <div className="grid gap-3"><label className="text-xs font-semibold">Document type<select name="document_type" required defaultValue={text(action.document?.document_type)} className={`${fieldClass} mt-1`}><option value="">Select document type</option>{options?.document_types.map((type) => <option key={type} value={type}>{humanize(type)}</option>)}</select></label><label className="text-xs font-semibold">PDF, DOC/DOCX, JPG or PNG (max 20 MB)<input name="document" required type="file" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" className={`${fieldClass} mt-1 file:mr-2 file:border-0 file:bg-transparent file:font-semibold`} /></label>{action.document ? <input type="hidden" name="replaces_document_id" value={Number(action.document.id)} /> : null}{!options?.document_upload_enabled ? <p className="text-xs text-muted-foreground">Storage is not configured. Uploads remain disabled.</p> : null}</div>;
    case "record_interview":
      return <div className="grid gap-3"><label className="text-xs font-semibold">Result<select required name="result" className={`${fieldClass} mt-1`}><option value="passed">Passed</option><option value="failed">Failed</option><option value="on_hold">On hold</option><option value="additional_interview">Additional interview</option><option value="candidate_withdrew">Candidate withdrew</option></select></label><label className="text-xs font-semibold">Format<input name="interview_format" className={`${fieldClass} mt-1`} /></label><label className="text-xs font-semibold">Notes<textarea name="notes" className={`${fieldClass} mt-1 min-h-24`} /></label><label className="text-xs font-semibold">HR recommendation<textarea name="hr_recommendation" className={`${fieldClass} mt-1 min-h-24`} /></label></div>;
    case "record_test":
      return <div className="grid gap-3"><div className="grid gap-3 sm:grid-cols-2"><label className="text-xs font-semibold">Score<input name="score" type="number" min="0" step="0.01" className={`${fieldClass} mt-1`} /></label><label className="text-xs font-semibold">Maximum score<input name="maximum_score" type="number" min="0.01" step="0.01" className={`${fieldClass} mt-1`} /></label></div><label className="text-xs font-semibold">Result<select name="result" className={`${fieldClass} mt-1`}><option value="passed">Passed</option><option value="failed">Failed</option><option value="retake_required">Retake required</option><option value="not_completed">Not completed</option></select></label><label className="text-xs font-semibold">Notes<textarea name="notes" className={`${fieldClass} mt-1 min-h-24`} /></label></div>;
    case "record_demo":
      return <div className="grid gap-3"><label className="text-xs font-semibold">Topic<input name="topic" className={`${fieldClass} mt-1`} /></label><label className="text-xs font-semibold">Score (0–10)<input name="score" type="number" min="0" max="10" step="0.01" className={`${fieldClass} mt-1`} /></label><label className="text-xs font-semibold">Result<select name="result" className={`${fieldClass} mt-1`}><option value="passed">Passed</option><option value="failed">Failed</option><option value="additional_demo">Additional demo</option><option value="on_hold">On hold</option></select></label><label className="text-xs font-semibold">Overview<textarea name="overview" className={`${fieldClass} mt-1 min-h-24`} /></label><label className="text-xs font-semibold">Academic recommendation<textarea name="recommendation" className={`${fieldClass} mt-1 min-h-24`} /></label></div>;
    case "assign_evaluators": {
      const assigned = new Set((candidate.assignments || []).map((item) => Number(item.assignee_account_id)));
      const evaluators = options?.staff.filter((person) => ["academic_director", "head_of_department"].includes(person.role)) || [];
      return <fieldset><legend className="text-xs font-semibold">Assigned evaluators</legend><div className="mt-2 space-y-2">{evaluators.map((person) => <label key={person.id} className="flex min-h-11 items-center gap-3 rounded-lg border border-border px-3 text-sm"><input type="checkbox" name="assignee_account_ids" value={person.id} defaultChecked={assigned.has(person.id)} className="h-4 w-4" /><span><span className="font-semibold">{person.name}</span><span className="ml-2 text-xs text-muted-foreground">{humanize(person.role)}</span></span></label>)}</div>{!evaluators.length ? <EmptyLine>No eligible evaluators.</EmptyLine> : null}</fieldset>;
    }
    case "request_approval":
      return <div className="grid gap-3"><label className="text-xs font-semibold">Requested outcome<select name="requested_outcome" className={`${fieldClass} mt-1`}><option value="teacher_academy">Teacher Academy</option><option value="active_teacher">Active Teacher</option></select></label><label className="text-xs font-semibold">Request note<textarea name="request_note" className={`${fieldClass} mt-1 min-h-24`} /></label></div>;
    case "record_outcome":
      return <div className="grid gap-3"><OutcomeFields candidate={candidate} options={options} /></div>;
    case "review_approval":
      return <div className="grid gap-3"><p className="rounded-lg bg-muted/50 p-3 text-sm">{action.status === "approved" ? `${stageLabels[text(action.approval.requested_outcome)]} will be approved and finalized. The onboarding record will remain pending.` : `${stageLabels[text(action.approval.requested_outcome)]} approval will be returned to HR.`}</p><label className="text-xs font-semibold">Comment<textarea name="review_comment" required={action.status === "returned"} defaultValue={action.status === "approved" ? "Approved and finalized by Academic Director." : ""} className={`${fieldClass} mt-1 min-h-24`} /></label></div>;
    case "add_task":
      return <div className="grid gap-3"><label className="text-xs font-semibold">Title<input required name="title" className={`${fieldClass} mt-1`} /></label><label className="text-xs font-semibold">Due date<input name="due_at" type="datetime-local" className={`${fieldClass} mt-1`} /></label><label className="text-xs font-semibold">Note<textarea name="note" className={`${fieldClass} mt-1 min-h-24`} /></label><input type="hidden" name="status" value="pending" /></div>;
    case "add_note":
      return <label className="text-xs font-semibold">Note<textarea autoFocus required name="body" className={`${fieldClass} mt-1 min-h-32`} /></label>;
  }
}

function actionTitle(action: ProfileAction | null) {
  if (!action) return "Candidate action";
  switch (action.kind) {
    case "edit_profile": return "Edit candidate profile";
    case "move_candidate": return "Move candidate";
    case "upload_document": return action.document ? "Replace document" : "Upload document";
    case "record_interview": return "Record interview";
    case "record_test": return "Record subject test";
    case "record_demo": return "Record demo lesson";
    case "assign_evaluators": return "Assign evaluators";
    case "request_approval": return "Request hiring approval";
    case "record_outcome": return "Record outcome";
    case "review_approval": return action.status === "approved" ? "Approve and finalize" : "Return request";
    case "add_task": return "Add task";
    case "add_note": return "Add note";
  }
}

function actionSubmitLabel(action: ProfileAction | null) {
  if (!action) return "Save";
  if (action.kind === "move_candidate") return "Move candidate";
  if (action.kind === "review_approval") return action.status === "approved" ? "Approve & finalize" : "Return request";
  if (action.kind === "upload_document") return action.document ? "Replace" : "Upload";
  return "Save";
}

export function CandidateProfile({ candidateId, basePath, role, onAnnouncement }: { candidateId: number; basePath: string; role: string; onAnnouncement: (message: string) => void }) {
  const queryClient = useQueryClient();
  const requestedTab = new URLSearchParams(window.location.search).get("tab") || "overview";
  const [tab, setTab] = useState<ProfileTab>(profileTabs.some((item) => item.key === requestedTab) ? requestedTab as ProfileTab : "overview");
  const [action, setAction] = useState<ProfileAction | null>(null);
  const [removeDocument, setRemoveDocument] = useState<Record<string, unknown> | null>(null);
  const formId = useId();
  const detail = useQuery({ queryKey: ["recruitment", "candidate", candidateId], queryFn: () => recruitmentRequest<RecruitmentCandidate>(`${RECRUITMENT_API}/candidates/${candidateId}`) });
  const options = useQuery({ queryKey: ["recruitment", "options"], queryFn: () => recruitmentRequest<RecruitmentOptions>(`${RECRUITMENT_API}/options`) });
  const mutation = useMutation({
    mutationFn: ({ url, method = "POST", values, formData }: { url: string; method?: string; values?: unknown; formData?: FormData }) => recruitmentRequest<MutationPayload>(url, { method, body: formData || jsonBody(values || {}) }),
    onSuccess: (result) => {
      onAnnouncement(result.message || "Recruitment record saved.");
      if (result.candidate) queryClient.setQueryData(["recruitment", "candidate", candidateId], result.candidate);
      const completedDirectorDecision = role === "academic_director" && (
        (action?.kind === "review_approval" && action.status === "approved")
        || action?.kind === "record_outcome"
      );
      if (completedDirectorDecision) {
        window.location.assign(`${basePath}/decisions?updated=1`);
        return;
      }
      setAction(null);
      setRemoveDocument(null);
      void queryClient.invalidateQueries({ queryKey: ["recruitment"] });
    },
    onError: (error) => onAnnouncement(queryError(error)),
  });

  useEffect(() => {
    const onPopState = () => {
      const next = new URLSearchParams(window.location.search).get("tab") || "overview";
      if (profileTabs.some((item) => item.key === next)) setTab(next as ProfileTab);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  if (detail.isLoading) return <PageState>Loading candidate profile…</PageState>;
  if (detail.error || !detail.data) return <PageState tone="error">{queryError(detail.error)}</PageState>;
  const candidate = detail.data;
  const permissions = candidate.permissions;
  const approved = (candidate.approvals || []).filter((item) => item.status === "approved");
  const pendingApprovals = (candidate.approvals || []).filter((item) => item.status === "requested");
  const latestInterview = candidate.interviews?.[0];
  const latestTest = candidate.subject_tests?.[0];
  const latestDemo = candidate.demo_lessons?.[0];
  const pendingTasks = (candidate.tasks || []).filter((task) => ["pending", "overdue"].includes(task.effective_status));

  const setProfileTab = (next: ProfileTab) => {
    const url = new URL(window.location.href);
    url.searchParams.set("tab", next);
    window.history.pushState({}, "", `${url.pathname}${url.search}`);
    setTab(next);
    window.scrollTo({ top: 0, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  };

  const handleTabKeyDown = (event: KeyboardEvent<HTMLButtonElement>, current: ProfileTab) => {
    const currentIndex = profileTabs.findIndex((item) => item.key === current);
    let nextIndex: number | null = null;
    if (event.key === "ArrowRight") nextIndex = (currentIndex + 1) % profileTabs.length;
    if (event.key === "ArrowLeft") nextIndex = (currentIndex - 1 + profileTabs.length) % profileTabs.length;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = profileTabs.length - 1;
    if (nextIndex === null) return;
    event.preventDefault();
    const next = profileTabs[nextIndex].key;
    setProfileTab(next);
    requestAnimationFrame(() => document.getElementById(`candidate-tab-${next}`)?.focus());
  };

  const params = new URLSearchParams(window.location.search);
  const origin = params.get("origin");
  const returnQuery = params.get("return") || "";
  const safeReturn = returnQuery.startsWith("?") ? returnQuery : "";
  const backHref = origin === "pipeline" ? `${basePath}/pipeline` : origin === "decisions" ? `${basePath}/decisions` : origin === "tasks" ? `${basePath}/tasks` : `${basePath}/candidates${safeReturn}`;
  const backLabel = origin === "pipeline" ? "Pipeline" : origin === "decisions" ? "Decisions" : origin === "tasks" ? "Tasks" : "Candidates";
  const backPath = origin === "pipeline" ? `${basePath}/pipeline` : origin === "decisions" ? `${basePath}/decisions` : origin === "tasks" ? `${basePath}/tasks` : `${basePath}/candidates`;

  const submit = (path: string, values: unknown, method = "POST") => mutation.mutate({ url: `${RECRUITMENT_API}/candidates/${candidateId}${path}`, method, values });
  const submitAction = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!action) return;
    const form = event.currentTarget;
    if (action.kind === "upload_document") {
      mutation.mutate({ url: `${RECRUITMENT_API}/candidates/${candidateId}/documents`, method: "POST", formData: new FormData(form) });
    } else if (action.kind === "edit_profile") {
      submit("", formValues(form), "PATCH");
    } else if (action.kind === "move_candidate") {
      submit("/stage", { ...formValues(form), expected_version: candidate.version });
    } else if (action.kind === "record_interview") {
      submit("/interviews", formValues(form));
    } else if (action.kind === "record_test") {
      submit("/subject-tests", { ...formValues(form), subject_id: candidate.subject_id || null });
    } else if (action.kind === "record_demo") {
      submit("/demo-lessons", { ...formValues(form), subject_id: candidate.subject_id || null });
    } else if (action.kind === "assign_evaluators") {
      const ids = new FormData(form).getAll("assignee_account_ids").map(Number).filter(Boolean);
      submit("/assignments", { assignee_account_ids: ids, subject_id: candidate.subject_id || null }, "PUT");
    } else if (action.kind === "request_approval") {
      submit("/approval-requests", formValues(form));
    } else if (action.kind === "record_outcome") {
      const values = formValues(form);
      submit("/final-decisions", { ...values, approval_id: values.approval_id ? Number(values.approval_id) : null });
    } else if (action.kind === "review_approval") {
      submit(`/approval-requests/${Number(action.approval.id)}/review`, { status: action.status, ...formValues(form) });
    } else if (action.kind === "add_task") {
      submit("/tasks", formValues(form));
    } else if (action.kind === "add_note") {
      submit("/notes", formValues(form));
    }
  };

  const evaluationItems: ActionMenuItem[] = [];
  if (permissions?.can_manage_interviews) evaluationItems.push({ key: "interview", label: "Record interview", onClick: () => setAction({ kind: "record_interview" }) });
  if (permissions?.can_add_academic_evaluation) {
    evaluationItems.push({ key: "test", label: "Record subject test", onClick: () => setAction({ kind: "record_test" }) });
    evaluationItems.push({ key: "demo", label: "Record demo lesson", onClick: () => setAction({ kind: "record_demo" }) });
  }
  const hiringItems: ActionMenuItem[] = [];
  if (permissions?.can_manage_assignments) hiringItems.push({ key: "assign", label: "Assign evaluators", onClick: () => setAction({ kind: "assign_evaluators" }) });
  if (permissions?.can_request_approval) hiringItems.push({ key: "request", label: "Request hiring approval", onClick: () => setAction({ kind: "request_approval" }) });
  if (permissions?.can_finalize || permissions?.can_reject || role === "hr_manager") hiringItems.push({ key: "outcome", label: permissions?.can_reject && !permissions?.can_finalize ? "Reject candidate" : "Record outcome", onClick: () => setAction({ kind: "record_outcome" }) });
  const activityItems: ActionMenuItem[] = [];
  if (permissions?.can_manage_tasks) activityItems.push({ key: "task", label: "Add task", onClick: () => setAction({ kind: "add_task" }) });
  if (permissions?.can_add_note) activityItems.push({ key: "note", label: "Add note", onClick: () => setAction({ kind: "add_note" }) });

  const overviewItems: ActionMenuItem[] = [];
  if (permissions?.can_move_stage && !["teacher_academy", "active_teacher"].includes(candidate.status)) {
    overviewItems.push({ key: "move", label: "Move candidate", onClick: () => setAction({ kind: "move_candidate" }) });
  }

  const tabAction = tab === "overview" && (permissions?.can_edit_profile || overviewItems.length)
    ? <div className="flex items-center gap-1">{permissions?.can_edit_profile ? <button type="button" className={buttonClass} aria-label="Edit profile" title="Edit profile" onClick={() => setAction({ kind: "edit_profile" })}><Pencil className="h-4 w-4" /><span className="hidden sm:inline">Edit profile</span></button> : null}{overviewItems.length ? <ActionMenu items={overviewItems} label="Candidate actions" /> : null}</div>
    : tab === "evaluations" && evaluationItems.length
      ? <ActionMenu items={evaluationItems} label="Add evaluation" />
      : tab === "documents" && permissions?.can_manage_documents
        ? <button type="button" className={buttonClass} aria-label="Upload document" title="Upload document" disabled={!options.data?.document_upload_enabled} onClick={() => setAction({ kind: "upload_document" })}><Plus className="h-4 w-4" /><span className="hidden sm:inline">Upload</span></button>
        : tab === "hiring" && hiringItems.length
          ? <ActionMenu items={hiringItems} label="Hiring actions" />
          : tab === "activity" && activityItems.length
            ? <ActionMenu items={activityItems} label="Activity actions" />
            : null;

  return (
    <div className="space-y-3">
      <header className="sticky top-[calc(var(--app-top-inset)+4.5rem)] z-20 rounded-xl border border-border bg-card/95 p-3 shadow-sm backdrop-blur lg:top-3">
        <div className="flex items-start gap-2">
          <a href={backHref} onClick={(event) => { try { const previous = new URL(document.referrer); if (origin && previous.origin === window.location.origin && previous.pathname === backPath) { event.preventDefault(); window.history.back(); } } catch { /* Direct deep links use the safe fallback href. */ } }} className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30" aria-label={`Back to ${backLabel}`} title={`Back to ${backLabel}`}><ArrowLeft className="h-4 w-4" /></a>
          <div className="min-w-0 flex-1 py-0.5"><div className="flex flex-wrap items-center gap-2"><h1 className="truncate text-lg font-bold tracking-tight sm:text-xl">{candidate.full_name}</h1><StatusBadge status={candidate.status}>{stageLabels[candidate.status] || humanize(candidate.status)}</StatusBadge></div><p className="mt-0.5 truncate text-xs text-muted-foreground">{candidate.applied_position || candidate.subject || "Position not set"}{candidate.next_task ? ` · Next: ${candidate.next_task.title}` : ""}</p></div>
          <div className="shrink-0">{tabAction}</div>
        </div>
        <label className="mt-2 block text-xs font-semibold text-muted-foreground sm:hidden">Profile section<select value={tab} onChange={(event) => setProfileTab(event.target.value as ProfileTab)} className={`${fieldClass} mt-1`}>{profileTabs.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select></label>
        <div className="mt-2 hidden gap-1 border-t border-border pt-2 sm:flex" role="tablist" aria-label="Candidate profile sections">
          {profileTabs.map((item) => <button key={item.key} id={`candidate-tab-${item.key}`} type="button" role="tab" tabIndex={tab === item.key ? 0 : -1} aria-selected={tab === item.key} aria-controls={`candidate-panel-${item.key}`} onClick={() => setProfileTab(item.key)} onKeyDown={(event) => handleTabKeyDown(event, item.key)} className={`min-h-11 rounded-lg px-3 text-[13px] font-semibold focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${tab === item.key ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"}`}>{item.label}</button>)}
        </div>
      </header>

      {tab === "overview" ? <div id="candidate-panel-overview" role="tabpanel" aria-labelledby="candidate-tab-overview" className="grid gap-3 xl:grid-cols-[minmax(0,2fr)_minmax(260px,1fr)]"><Panel title="Personal & background" icon={<UserRound className="h-4 w-4" />}><DefinitionGrid values={[["Phone", candidate.phone], ["Telegram", candidate.telegram_username], ["Application date", dateLabel(candidate.application_date)], ["Source", candidate.source], ["Age", candidate.age], ["English", candidate.english_level], ["Schedule", candidate.preferred_schedule], ["Availability", candidate.employment_availability], ["Start date", dateLabel(candidate.available_start_date)], ["Expected salary", candidate.expected_salary_uzs ? `${Number(candidate.expected_salary_uzs).toLocaleString()} UZS` : ""], ["Address", candidate.address], ["Previous workplace", candidate.previous_workplace]]} /><div className="mt-2"><DefinitionGrid values={[["Motivation", candidate.motivation_expectations], ["Work experience", candidate.work_experience], ["Teaching experience", candidate.teaching_experience], ["Interests", candidate.interests_hobbies]]} /></div></Panel><div className="space-y-3"><Panel title="Next action" icon={<CalendarClock className="h-4 w-4" />}>{candidate.next_task ? <div><p className="text-sm font-semibold">{candidate.next_task.title}</p><p className="mt-1 text-xs text-muted-foreground">Due {dateLabel(candidate.next_task.due_at)}</p></div> : <EmptyLine>No open task.</EmptyLine>}</Panel><Panel title="Readiness" icon={<BriefcaseBusiness className="h-4 w-4" />}><DefinitionGrid values={[["Missing documents", candidate.missing_document_types?.length || 0], ["Interview", latestInterview?.result], ["Subject test", latestTest?.result], ["Demo", latestDemo?.result], ["Open tasks", pendingTasks.length], ["Final decision", candidate.final_decision || "Pending"]]} /></Panel></div></div> : null}

      {tab === "evaluations" ? <div id="candidate-panel-evaluations" role="tabpanel" aria-labelledby="candidate-tab-evaluations" className="grid gap-3 xl:grid-cols-3"><Panel title="Interviews" icon={<ClipboardCheck className="h-4 w-4" />}><AttemptList items={candidate.interviews || []} empty="No interviews recorded." /></Panel><Panel title="Subject tests" icon={<ClipboardCheck className="h-4 w-4" />}><AttemptList items={candidate.subject_tests || []} empty="No subject tests recorded." /></Panel><Panel title="Demo lessons" icon={<ClipboardCheck className="h-4 w-4" />}><AttemptList items={candidate.demo_lessons || []} empty="No demo lessons recorded." /></Panel></div> : null}

      {tab === "documents" ? <div id="candidate-panel-documents" role="tabpanel" aria-labelledby="candidate-tab-documents"><Panel title="Documents" icon={<FileText className="h-4 w-4" />} action={<span className="text-xs text-muted-foreground">Missing: {candidate.missing_document_types?.length || 0}</span>}><div className="divide-y divide-border rounded-lg border border-border">{(candidate.documents || []).map((document) => { const documentItems: ActionMenuItem[] = [{ key: "open", label: "Open", onClick: () => window.open(`${RECRUITMENT_API}/candidates/${candidateId}/documents/${text(document.id)}/open`, "_blank", "noopener,noreferrer") }, { key: "download", label: "Download", onClick: () => window.location.assign(`${RECRUITMENT_API}/candidates/${candidateId}/documents/${text(document.id)}/open?download=true`) }]; if (permissions?.can_manage_documents) { documentItems.push({ key: "replace", label: "Replace", onClick: () => setAction({ kind: "upload_document", document }) }); documentItems.push({ separator: true, key: "separator" }); documentItems.push({ key: "remove", label: "Remove", danger: true, onClick: () => setRemoveDocument(document) }); } return <div key={Number(document.id)} className="flex min-h-14 items-center justify-between gap-2 px-3 py-2"><div className="min-w-0"><p className="truncate text-[13px] font-semibold">{text(document.original_file_name)}</p><p className="text-xs text-muted-foreground">{humanize(document.document_type)} · v{text(document.version)}</p></div><ActionMenu items={documentItems} label={`Actions for ${text(document.original_file_name)}`} /></div>; })}</div>{!(candidate.documents || []).length ? <EmptyLine>No documents uploaded.</EmptyLine> : null}<p className="mt-3 text-xs leading-5 text-muted-foreground">Missing document types remain informational: {(candidate.missing_document_types || []).map(humanize).join(", ") || "none"}.</p></Panel></div> : null}

      {tab === "hiring" ? <div id="candidate-panel-hiring" role="tabpanel" aria-labelledby="candidate-tab-hiring" className="space-y-3"><Panel title="Under-review summary" icon={<ShieldCheck className="h-4 w-4" />}><DefinitionGrid values={Object.entries(candidate.under_review || {}).map(([key, value]) => [humanize(key), value])} /></Panel><div className="grid gap-3 xl:grid-cols-3"><Panel title="Assignments" icon={<UserRound className="h-4 w-4" />}><div className="space-y-2">{(candidate.assignments || []).map((item) => <article key={Number(item.id)} className="rounded-lg border border-border p-3"><p className="text-[13px] font-semibold">{text(item.assignee_name)}</p><p className="mt-1 text-xs text-muted-foreground">{humanize(item.assignee_role)}{item.subject ? ` · ${text(item.subject)}` : ""}</p></article>)}{!(candidate.assignments || []).length ? <EmptyLine>No evaluators assigned.</EmptyLine> : null}</div></Panel><Panel title="Approval requests" icon={<ShieldCheck className="h-4 w-4" />}><div className="space-y-2">{(candidate.approvals || []).map((item) => { const reviewItems: ActionMenuItem[] = !permissions?.can_review_approval ? [] : item.status === "requested" ? [{ key: "approve", label: "Approve & finalize", onClick: () => setAction({ kind: "review_approval", approval: item, status: "approved" }) }, { key: "return", label: "Return with comment", onClick: () => setAction({ kind: "review_approval", approval: item, status: "returned" }) }] : item.status === "approved" ? [{ key: "finalize", label: "Finalize approved request", onClick: () => setAction({ kind: "review_approval", approval: item, status: "approved" }) }] : []; return <article key={Number(item.id)} className="rounded-lg border border-border p-3"><div className="flex items-center justify-between gap-2"><div><p className="text-[13px] font-semibold">{stageLabels[text(item.requested_outcome)]}</p><p className="mt-1 text-xs text-muted-foreground">{text(item.request_note || "No request note")}</p></div><div className="flex items-center gap-1"><StatusBadge status={text(item.status)} />{reviewItems.length ? <ActionMenu items={reviewItems} label={`Review approval ${text(item.id)}`} /> : null}</div></div>{item.review_comment ? <p className="mt-2 rounded-md bg-muted/50 px-2 py-1.5 text-xs text-muted-foreground">Review: {text(item.review_comment)}{item.reviewed_by ? ` · ${text(item.reviewed_by)}` : ""}</p> : null}</article>; })}{!(candidate.approvals || []).length ? <EmptyLine>No approval requests.</EmptyLine> : null}</div></Panel><Panel title="Final decisions" icon={<BriefcaseBusiness className="h-4 w-4" />}><div className="space-y-2">{(candidate.decisions || []).map((item) => <article key={Number(item.id)} className="rounded-lg border border-border p-3"><div className="flex items-center justify-between"><span className="text-[13px] font-semibold">{stageLabels[text(item.decision)]}</span><span className="text-xs text-muted-foreground">{dateLabel(item.created_at)}</span></div><p className="mt-1 text-xs text-muted-foreground">{humanize(item.rejection_reason) || text(item.reason_detail || "No reason")}</p></article>)}{!(candidate.decisions || []).length ? <EmptyLine>No final decision.</EmptyLine> : null}</div></Panel></div>{pendingApprovals.length ? <p className="text-xs text-muted-foreground">The Academic Director can approve and finalize the requested outcome or return it to HR.</p> : null}{approved.length ? <p className="text-xs text-muted-foreground">Legacy approved requests remain available for finalization.</p> : null}</div> : null}

      {tab === "activity" ? <div id="candidate-panel-activity" role="tabpanel" aria-labelledby="candidate-tab-activity" className="grid gap-3 xl:grid-cols-3"><Panel title="Tasks" icon={<CalendarClock className="h-4 w-4" />}><div className="space-y-2">{(candidate.tasks || []).map((task) => <article key={task.id} className="flex min-h-14 items-center justify-between gap-3 rounded-lg border border-border p-3"><div className="min-w-0"><p className="truncate text-[13px] font-semibold">{task.title}</p><p className="text-xs text-muted-foreground">{dateLabel(task.due_at)}</p></div><StatusBadge status={task.effective_status} /></article>)}{!(candidate.tasks || []).length ? <EmptyLine>No tasks.</EmptyLine> : null}</div></Panel><Panel title="Notes" icon={<MessageSquareText className="h-4 w-4" />}><div className="space-y-2">{(candidate.notes || []).map((note) => <article key={Number(note.id)} className="rounded-lg border border-border p-3"><p className="whitespace-pre-wrap text-[13px] leading-5">{text(note.body)}</p><p className="mt-2 text-xs text-muted-foreground">{text(note.author || "Unknown actor")} · {dateLabel(note.created_at)}</p></article>)}{!(candidate.notes || []).length ? <EmptyLine>No notes.</EmptyLine> : null}</div></Panel><Panel title="Timeline" icon={<Activity className="h-4 w-4" />}><ol className="space-y-3">{(candidate.activity || []).map((item) => <li key={Number(item.id)} className="border-l-2 border-primary/30 pl-3"><p className="text-[13px] font-semibold">{humanize(item.event_type)}</p><p className="mt-0.5 text-xs text-muted-foreground">{text(item.actor || "System")} · {dateLabel(item.created_at)}</p></li>)}{!(candidate.activity || []).length ? <EmptyLine>No activity yet.</EmptyLine> : null}</ol></Panel></div> : null}

      <Drawer
        open={Boolean(action)}
        onClose={() => { if (!mutation.isPending) { mutation.reset(); setAction(null); } }}
        title={actionTitle(action)}
        description={candidate.full_name}
        widthClass="sm:max-w-xl"
        footer={action ? <div className="flex justify-end gap-2"><button type="button" className={secondaryButtonClass} disabled={mutation.isPending} onClick={() => { mutation.reset(); setAction(null); }}>Cancel</button><button type="submit" form={formId} className={buttonClass} disabled={mutation.isPending || (action.kind === "upload_document" && !options.data?.document_upload_enabled)}>{mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}{actionSubmitLabel(action)}</button></div> : undefined}
      >
        {mutation.error ? <div role="alert" className="mb-3 rounded-lg border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive">{queryError(mutation.error)}</div> : null}
        {action ? <form id={formId} onSubmit={submitAction}><ActionFields action={action} candidate={candidate} options={options.data} /></form> : null}
      </Drawer>

      <ConfirmDialog
        open={Boolean(removeDocument)}
        title="Remove document?"
        message={<>The stored object for <strong>{text(removeDocument?.original_file_name)}</strong> will be deleted while its audit metadata remains.</>}
        confirmLabel="Remove"
        danger
        busy={mutation.isPending}
        onCancel={() => setRemoveDocument(null)}
        onConfirm={() => {
          if (removeDocument) mutation.mutate({ url: `${RECRUITMENT_API}/candidates/${candidateId}/documents/${Number(removeDocument.id)}`, method: "DELETE" });
        }}
      />
    </div>
  );
}
