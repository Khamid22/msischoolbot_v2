import { useEffect, useMemo, useRef, useState } from "react";
import { CheckCircle2, ClipboardCheck, GraduationCap, Info, Pencil, Plus, Trash2, Users, XCircle } from "lucide-react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { routes } from "@/shared/lib/routes";
import { asNumber, asString } from "../shared";
import { TeacherTab, ToastTone, Candidate, Teacher, TAB_STORAGE_KEY, TRAINING_FILTER_STORAGE_KEY, DETAIL_CANDIDATE_STORAGE_KEY, tabs, hiringStages, TRAINING_TARGET_LESSONS, HIRING_STAGE_PAGE_SIZE, TABLE_PAGE_SIZE, teacherCategoryLabel, postForm, trainingMeta } from "./teachers/shared";
import { PaginationControls } from "./teachers/controls";
import { CandidateCard } from "./teachers/CandidateCard";
import { CandidateDetailModal } from "./teachers/CandidateDetailModal";
import { CandidateModal } from "./teachers/CandidateModal";
import { PromoteModal } from "./teachers/PromoteModal";
import { TeacherAssignmentModal } from "./teachers/TeacherAssignmentModal";
import { TeacherAcademyPanel } from "./teachers/TeacherAcademyPanel";
import { RubricModal, TrainingEvaluationModal } from "./teachers/TrainingEvaluationModal";

export default function TeachersPanel({
  state,
  view = "combined",
}: {
  state: any;
  view?: "combined" | "candidates" | "teachers";
}) {
  const { teacherEdit, props, currentSchool } = state;
  const csrf: string = props.csrfToken || "";

  const isAcademicDirector = asString(state.adminMode).toLowerCase() === "academic_director";
  const defaultTab: TeacherTab = isAcademicDirector ? "academy" : view === "teachers" ? "active" : "hiring";
  const visibleTabs = useMemo(
    () =>
      isAcademicDirector
        ? tabs.filter((tab) => tab.key === "academy" || tab.key === "active")
        : view === "candidates"
        ? tabs.filter((tab) => tab.key === "hiring" || tab.key === "training")
        : view === "teachers"
          ? tabs.filter((tab) => tab.key === "active")
          : tabs,
    [isAcademicDirector, view],
  );

  const [activeTab, setActiveTab] = useState<TeacherTab>(() => {
    if (view !== "combined") {
      return defaultTab;
    }
    if (typeof window !== "undefined") {
      const saved = window.sessionStorage.getItem(TAB_STORAGE_KEY);
      if (saved === "hiring" || saved === "training" || saved === "academy" || saved === "active") {
        return saved;
      }
    }
    return defaultTab;
  });

  const [teachers, setTeachers] = useState<Teacher[]>(
    Array.isArray(state.teachers) ? state.teachers : [],
  );
  const [candidates, setCandidates] = useState<Candidate[]>(
    Array.isArray(props.adminTeacherCandidates) ? props.adminTeacherCandidates : [],
  );
  const [academyTeachers, setAcademyTeachers] = useState<Array<Record<string, unknown>>>(
    Array.isArray(props.adminTeacherAcademy) ? props.adminTeacherAcademy : [],
  );

  const [modalOpen, setModalOpen] = useState(Boolean(teacherEdit));
  const [candidateOpen, setCandidateOpen] = useState(false);
  const [trainingCandidate, setTrainingCandidate] = useState<Candidate | null>(null);
  const [editingTrainingEvent, setEditingTrainingEvent] = useState<Record<string, unknown> | null>(null);
  const [busyCandidateId, setBusyCandidateId] = useState<number | null>(null);
  const [teacherSubmitting, setTeacherSubmitting] = useState(false);
  const [candidateSubmitting, setCandidateSubmitting] = useState(false);
  const [modalError, setModalError] = useState("");
  const [candidateError, setCandidateError] = useState("");
  const [rubricOpen, setRubricOpen] = useState(false);
  const [detailCandidateId, setDetailCandidateId] = useState<number | null>(null);
  const [promoteCandidate, setPromoteCandidate] = useState<Candidate | null>(null);
  const [promoteSubmitting, setPromoteSubmitting] = useState(false);
  const [promoteError, setPromoteError] = useState("");
  const [trainingFilter, setTrainingFilter] = useState<"in_training" | "passed" | "rejected">(() => {
    if (typeof window !== "undefined") {
      const saved = window.sessionStorage.getItem(TRAINING_FILTER_STORAGE_KEY);
      if (saved === "in_training" || saved === "passed" || saved === "rejected") {
        return saved;
      }
    }
    return "in_training";
  });
  const [trainingSearch, setTrainingSearch] = useState("");
  const [trainingSort, setTrainingSort] = useState<"recent" | "progress" | "average" | "name">("recent");
  const [toast, setToast] = useState<{ message: string; tone: ToastTone } | null>(null);
  const [stagePages, setStagePages] = useState<Record<string, number>>({});
  const [trainingPage, setTrainingPage] = useState(1);
  const [teacherPage, setTeacherPage] = useState(1);
  const toastTimer = useRef<number | null>(null);

  useEffect(() => {
    if (!visibleTabs.some((tab) => tab.key === activeTab)) {
      setActiveTab(defaultTab);
    }
  }, [activeTab, defaultTab, visibleTabs]);

  useEffect(() => {
    return () => {
      if (toastTimer.current) {
        window.clearTimeout(toastTimer.current);
      }
    };
  }, []);

  useEffect(() => {
    if (Array.isArray(props.adminTeacherAcademy)) {
      setAcademyTeachers(props.adminTeacherAcademy);
    }
  }, [props.adminTeacherAcademy]);

  useEffect(() => {
    try {
      const saved = window.sessionStorage.getItem(DETAIL_CANDIDATE_STORAGE_KEY);
      if (!saved) {
        return;
      }
      const parsed = Number(saved);
      window.sessionStorage.removeItem(DETAIL_CANDIDATE_STORAGE_KEY);
      if (Number.isFinite(parsed) && parsed > 0) {
        setDetailCandidateId(parsed);
      }
    } catch {
    }
  }, []);

  useEffect(() => {
    try {
      window.sessionStorage.setItem(TRAINING_FILTER_STORAGE_KEY, trainingFilter);
    } catch {
    }
  }, [trainingFilter]);

  function showToast(message: string, tone: ToastTone = "success") {
    setToast({ message, tone });
    if (toastTimer.current) {
      window.clearTimeout(toastTimer.current);
    }
    toastTimer.current = window.setTimeout(() => setToast(null), 2600);
  }

  function selectTab(tab: TeacherTab) {
    setActiveTab(tab);
    if (view === "combined") {
      try {
        window.sessionStorage.setItem(TAB_STORAGE_KEY, tab);
      } catch {
      }
    }
  }

  function clearEditUrl() {
    if (teacherEdit && window.history?.replaceState) {
      window.history.replaceState(
        {},
        "",
        `/?panel=teachers&school=${encodeURIComponent(currentSchool)}`,
      );
    }
  }

  async function runCandidateAction(
    candidateId: number,
    fields: Record<string, string>,
    opts?: { confirmMessage?: string },
  ) {
    if (opts?.confirmMessage && !window.confirm(opts.confirmMessage)) {
      return;
    }
    setBusyCandidateId(candidateId);
    const { ok, data } = await postForm(routes.adminTeacherCandidateStatus(candidateId), fields, csrf);
    setBusyCandidateId(null);
    if (!ok) {
      showToast(asString(data.message) || "Could not update candidate.", "danger");
      return;
    }
    if (Array.isArray(data.candidates)) {
      setCandidates(data.candidates as Candidate[]);
    }
    showToast(asString(data.message) || "Candidate updated.");
  }

  async function saveTrainingEvaluation(
    candidateId: number,
    eventId: number | null,
    fields: Record<string, string>,
  ) {
    setBusyCandidateId(candidateId);
    const url =
      eventId !== null
        ? routes.adminTeacherCandidateEventEdit(candidateId, eventId)
        : routes.adminTeacherCandidateStatus(candidateId);
    const { ok, data } = await postForm(url, fields, csrf);
    setBusyCandidateId(null);
    if (!ok) {
      showToast(asString(data.message) || "Could not save evaluation.", "danger");
      return;
    }
    if (Array.isArray(data.candidates)) {
      setCandidates(data.candidates as Candidate[]);
    }
    setTrainingCandidate(null);
    setEditingTrainingEvent(null);
    showToast(asString(data.message) || (eventId !== null ? "Evaluation updated." : "Evaluation saved."));
  }

  async function deleteTrainingEvaluation(candidateId: number, eventId: number) {
    if (!window.confirm("Delete this lesson evaluation?")) {
      return;
    }
    setBusyCandidateId(candidateId);
    const { ok, data } = await postForm(routes.adminTeacherCandidateEventDelete(candidateId, eventId), {}, csrf);
    setBusyCandidateId(null);
    if (!ok) {
      showToast(asString(data.message) || "Could not delete evaluation.", "danger");
      return;
    }
    if (Array.isArray(data.candidates)) {
      setCandidates(data.candidates as Candidate[]);
    }
    showToast(asString(data.message) || "Evaluation deleted.");
  }

  async function submitCandidate(fields: Record<string, string>) {
    setCandidateSubmitting(true);
    setCandidateError("");
    const { ok, data } = await postForm(routes.adminTeacherCandidateCreate, fields, csrf);
    setCandidateSubmitting(false);
    if (!ok) {
      setCandidateError(asString(data.message) || "Could not add candidate.");
      return;
    }
    if (Array.isArray(data.candidates)) {
      setCandidates(data.candidates as Candidate[]);
    }
    setCandidateOpen(false);
    showToast(asString(data.message) || "Candidate added.");
  }

  async function submitTeacher(fields: Record<string, string>) {
    setTeacherSubmitting(true);
    setModalError("");
    const url = teacherEdit
      ? routes.adminTeacherUpdate(asNumber(teacherEdit.id))
      : routes.adminTeacherCreate;
    const { ok, data } = await postForm(url, fields, csrf);
    setTeacherSubmitting(false);
    if (!ok) {
      setModalError(asString(data.message) || "Could not save teacher.");
      return;
    }
    if (Array.isArray(data.teachers)) {
      setTeachers(data.teachers as Teacher[]);
    }
    setModalOpen(false);
    clearEditUrl();
    showToast(asString(data.message) || "Teacher saved.");
  }

  async function deleteTeacher(teacherId: number, teacherName: string) {
    if (!window.confirm(`Delete ${teacherName || "this teacher"}?`)) {
      return;
    }
    const { ok, data } = await postForm(routes.adminTeacherDelete(teacherId), {}, csrf);
    if (!ok) {
      showToast(asString(data.message) || "Could not delete teacher.", "danger");
      return;
    }
    if (Array.isArray(data.teachers)) {
      setTeachers(data.teachers as Teacher[]);
    }
    showToast(asString(data.message) || "Teacher deleted.");
  }

  function closeTeacherModal() {
    setModalOpen(false);
    setModalError("");
    clearEditUrl();
  }

  async function runPromote(candidateId: number, fields: Record<string, string>) {
    setPromoteSubmitting(true);
    setPromoteError("");
    const { ok, data } = await postForm(routes.adminTeacherCandidatePromote(candidateId), fields, csrf);
    setPromoteSubmitting(false);
    if (!ok) {
      setPromoteError(asString(data.message) || "Could not promote candidate.");
      return;
    }
    if (Array.isArray(data.teachers)) {
      setTeachers(data.teachers as Teacher[]);
    }
    if (Array.isArray(data.candidates)) {
      setCandidates(data.candidates as Candidate[]);
    }
    setPromoteCandidate(null);
    setDetailCandidateId(null);
    showToast(asString(data.message) || "Candidate promoted.");
  }

  const activeCandidates = candidates.filter((candidate) => {
    const status = asString(candidate.status) || "new";
    return !["rejected", "withdrawn", "hired"].includes(status);
  });
  const closedCandidates = candidates.filter((candidate) => {
    const status = asString(candidate.status) || "new";
    return ["rejected", "withdrawn"].includes(status);
  });
  const trainingCandidates = candidates.filter(
    (candidate) => ["training_ready", "training_passed"].includes(asString(candidate.status)),
  );
  const inTrainingCount = trainingCandidates.filter(
    (candidate) => asString(candidate.status) === "training_ready",
  ).length;
  const trainingPassedCount = trainingCandidates.filter(
    (candidate) => asString(candidate.status) === "training_passed",
  ).length;
  const rejectedCandidates = closedCandidates;

  // Always re-read the open candidate from the live list so the detail view
  // reflects the latest data after an async action.
  const detailCandidate =
    detailCandidateId !== null
      ? candidates.find((candidate) => asNumber(candidate.id) === detailCandidateId) || null
      : null;

  const trainingFilterCounts = {
    in_training: inTrainingCount,
    passed: trainingPassedCount,
    rejected: rejectedCandidates.length,
  };
  const trainingFilters: Array<{
    key: "in_training" | "passed" | "rejected";
    label: string;
    tone: string;
  }> = [
    { key: "in_training", label: "In training", tone: "" },
    { key: "passed", label: "Awaiting decision", tone: "text-emerald-700" },
    { key: "rejected", label: "Rejected", tone: "text-destructive" },
  ];

  const trainingBase =
    trainingFilter === "passed"
      ? candidates.filter((candidate) => asString(candidate.status) === "training_passed")
      : trainingFilter === "rejected"
        ? rejectedCandidates
        : candidates.filter((candidate) => asString(candidate.status) === "training_ready");

  const trainingSearchNorm = trainingSearch.trim().toLowerCase();
  const trainingRows = trainingBase
    .filter((candidate) => {
      if (!trainingSearchNorm) return true;
      return (
        asString(candidate.full_name).toLowerCase().includes(trainingSearchNorm) ||
        asString(candidate.subject).toLowerCase().includes(trainingSearchNorm)
      );
    })
    .sort((a, b) => {
      const metaA = trainingMeta(a);
      const metaB = trainingMeta(b);
      if (trainingSort === "name") {
        return asString(a.full_name).localeCompare(asString(b.full_name));
      }
      if (trainingSort === "progress") {
        return metaB.lessonCount - metaA.lessonCount;
      }
      if (trainingSort === "average") {
        return metaB.average - metaA.average;
      }
      return asString(b.updated_at).localeCompare(asString(a.updated_at));
    });
  const trainingTotalPages = Math.max(1, Math.ceil(trainingRows.length / TABLE_PAGE_SIZE));
  const effectiveTrainingPage = Math.min(trainingPage, trainingTotalPages);
  const pagedTrainingRows = trainingRows.slice(
    (effectiveTrainingPage - 1) * TABLE_PAGE_SIZE,
    effectiveTrainingPage * TABLE_PAGE_SIZE,
  );
  const teacherTotalPages = Math.max(1, Math.ceil(teachers.length / TABLE_PAGE_SIZE));
  const effectiveTeacherPage = Math.min(teacherPage, teacherTotalPages);
  const pagedTeachers = teachers.slice(
    (effectiveTeacherPage - 1) * TABLE_PAGE_SIZE,
    effectiveTeacherPage * TABLE_PAGE_SIZE,
  );

  useEffect(() => {
    setTrainingPage(1);
  }, [trainingFilter, trainingSearch, trainingSort]);

  useEffect(() => {
    setTeacherPage(1);
  }, [teachers.length]);

  return (
    <div className="workspace-fit flex flex-col gap-3 lg:h-full lg:min-h-0">
      {toast ? (
        <div
          className={`fixed right-4 top-[calc(var(--app-top-inset)+4rem)] lg:top-4 z-[60] flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-bold shadow-card-hover ${
            toast.tone === "danger" ? "bg-destructive text-destructive-foreground" : "bg-foreground text-background"
          }`}
          role="status"
        >
          {toast.tone === "danger" ? <XCircle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
          {toast.message}
        </div>
      ) : null}

      {modalOpen ? (
        <TeacherAssignmentModal
          state={state}
          isEdit={Boolean(teacherEdit)}
          submitting={teacherSubmitting}
          error={modalError}
          onSubmit={submitTeacher}
          onClose={closeTeacherModal}
        />
      ) : null}
      {candidateOpen ? (
        <CandidateModal
          csrf={csrf}
          submitting={candidateSubmitting}
          error={candidateError}
          onSubmit={submitCandidate}
          onClose={() => {
            setCandidateOpen(false);
            setCandidateError("");
          }}
        />
      ) : null}
      {trainingCandidate ? (
        <TrainingEvaluationModal
          candidate={trainingCandidate}
          editingEvent={editingTrainingEvent}
          busy={busyCandidateId === asNumber(trainingCandidate.id)}
          onSave={saveTrainingEvaluation}
          onClose={() => {
            setTrainingCandidate(null);
            setEditingTrainingEvent(null);
          }}
        />
      ) : null}
      {rubricOpen ? <RubricModal onClose={() => setRubricOpen(false)} /> : null}
      {detailCandidate ? (
        <CandidateDetailModal
          candidate={detailCandidate}
          busy={busyCandidateId === asNumber(detailCandidate.id)}
          onClose={() => setDetailCandidateId(null)}
          onAddEvaluation={() => {
            setEditingTrainingEvent(null);
            setTrainingCandidate(detailCandidate);
            setDetailCandidateId(null);
          }}
          onAction={runCandidateAction}
          onPromote={() => {
            setPromoteError("");
            setPromoteCandidate(detailCandidate);
          }}
          onEditEvent={(event) => {
            setEditingTrainingEvent(event);
            setTrainingCandidate(detailCandidate);
            setDetailCandidateId(null);
          }}
          onDeleteEvent={(eventId) => deleteTrainingEvaluation(asNumber(detailCandidate.id), eventId)}
        />
      ) : null}
      {promoteCandidate ? (
        <PromoteModal
          candidate={promoteCandidate}
          state={state}
          submitting={promoteSubmitting}
          error={promoteError}
          onSubmit={runPromote}
          onClose={() => setPromoteCandidate(null)}
        />
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-3">
        {visibleTabs.length > 1 ? (
          <div className="inline-flex rounded-lg border border-foreground/10 bg-surface p-1 shadow-card">
            {visibleTabs.map((tab) => {
              const isActive = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => selectTab(tab.key)}
                  className={`rounded-md px-3 py-2 text-left text-xs font-bold transition-colors sm:px-4 ${
                    isActive ? "bg-foreground text-background" : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`}
                >
                  <span className="block">{tab.label}</span>
                  <span
                    className={`hidden text-[10px] font-semibold sm:block ${
                      isActive ? "text-background/70" : "text-muted-foreground"
                    }`}
                  >
                    {tab.hint}
                  </span>
                </button>
              );
            })}
          </div>
        ) : (
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
              HR Manager / {activeTab === "active" ? "Teachers" : "Candidates"}
            </p>
            <h2 className="text-2xl font-bold">
              {activeTab === "active" ? "Teachers" : activeTab === "training" ? "Training" : "Candidates"}
            </h2>
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          {activeTab === "hiring" ? (
            <button
              type="button"
              onClick={() => {
                setCandidateError("");
                setCandidateOpen(true);
              }}
              className="inline-flex h-9 items-center gap-2 rounded-lg bg-primary px-3 text-sm font-bold text-primary-foreground"
            >
              <Plus className="h-4 w-4" />
              Add Candidate
            </button>
          ) : null}
          {activeTab === "active" ? (
            <button
              type="button"
              onClick={() => {
                setModalError("");
                setModalOpen(true);
              }}
              className="inline-flex h-9 items-center gap-2 rounded-lg bg-primary px-3 text-sm font-bold text-primary-foreground"
            >
              <Plus className="h-4 w-4" />
              Assign Teacher
            </button>
          ) : null}
        </div>
      </div>

      {activeTab === "hiring" ? (
        <ChartCard
          title="Hiring Pipeline"
          subtitle={`${activeCandidates.length} active · ${closedCandidates.length} closed`}
          icon={<ClipboardCheck className="h-4 w-4 text-info" />}
          className="flex min-h-0 flex-1 flex-col"
          bodyClassName="flex min-h-0 flex-1 flex-col"
        >
          <div className="grid w-full flex-1 grid-cols-1 gap-3 md:grid-cols-2 lg:min-h-[30rem] lg:grid-cols-4">
            {hiringStages.map((stage) => {
              const stageCandidates = activeCandidates.filter(
                (candidate) => (asString(candidate.status) || "new") === stage.key,
              );
              const totalPages = Math.max(1, Math.ceil(stageCandidates.length / HIRING_STAGE_PAGE_SIZE));
              const page = Math.min(stagePages[stage.key] || 1, totalPages);
              const pagedCandidates = stageCandidates.slice(
                (page - 1) * HIRING_STAGE_PAGE_SIZE,
                page * HIRING_STAGE_PAGE_SIZE,
              );
              return (
                <div
                  key={stage.key}
                  className="flex min-h-0 min-w-0 flex-col rounded-lg border border-foreground/8 bg-background p-2.5"
                >
                  <div className="mb-2.5 flex shrink-0 items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-bold">{stage.title}</p>
                      <p className="text-[11px] leading-4 text-muted-foreground">{stage.detail}</p>
                    </div>
                    <span className="shrink-0 rounded-md bg-muted px-2 py-1 text-[11px] font-bold text-muted-foreground">
                      {stageCandidates.length}
                    </span>
                  </div>

                  <div className="grid min-h-0 flex-1 content-start gap-2">
                    {stageCandidates.length ? (
                      pagedCandidates.map((candidate) => (
                        <CandidateCard
                          key={asNumber(candidate.id)}
                          candidate={candidate}
                          busy={busyCandidateId === asNumber(candidate.id)}
                          onAction={runCandidateAction}
                        />
                      ))
                    ) : (
                      <div className="rounded-lg border border-dashed border-foreground/12 bg-surface/60 px-3 py-6 text-center">
                        <p className="text-xs font-bold text-muted-foreground">No candidates</p>
                      </div>
                    )}
                  </div>
                  <PaginationControls
                    page={page}
                    totalPages={totalPages}
                    onPageChange={(nextPage) => setStagePages((prev) => ({ ...prev, [stage.key]: nextPage }))}
                    label={`${stageCandidates.length} total`}
                  />
                </div>
              );
            })}
          </div>
        </ChartCard>
      ) : null}

      {activeTab === "academy" ? (
        <TeacherAcademyPanel
          state={state}
          academyTeachers={academyTeachers}
          onAcademyChange={setAcademyTeachers}
          onTeachersChange={(rows) => setTeachers(rows as Teacher[])}
          showToast={showToast}
        />
      ) : null}

      {activeTab === "training" ? (
        <ChartCard
          title="Training"
          subtitle={`${inTrainingCount} in training · ${trainingPassedCount} awaiting decision`}
          icon={<GraduationCap className="h-4 w-4 text-info" />}
          className="flex min-h-0 flex-1 flex-col"
          bodyClassName="flex min-h-0 flex-1 flex-col"
          headerActions={
            <button
              type="button"
              onClick={() => setRubricOpen(true)}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-foreground/10 bg-surface px-3 text-xs font-bold text-foreground hover:bg-muted"
            >
              <Info className="h-3.5 w-3.5 text-info" />
              How grading works
            </button>
          }
        >
          <div className="mb-3 grid shrink-0 grid-cols-3 gap-2">
            {trainingFilters.map((filter) => {
              const isActive = trainingFilter === filter.key;
              return (
                <button
                  key={filter.key}
                  type="button"
                  onClick={() => setTrainingFilter(filter.key)}
                  className={`rounded-lg border px-3 py-2.5 text-left transition-colors ${
                    isActive
                      ? "border-foreground/30 bg-background ring-2 ring-foreground/15"
                      : "border-foreground/8 bg-background hover:bg-muted"
                  }`}
                >
                  <p className={`text-lg font-bold leading-none ${filter.tone}`}>
                    {trainingFilterCounts[filter.key]}
                  </p>
                  <p className="mt-1 text-[11px] font-semibold text-muted-foreground">{filter.label}</p>
                </button>
              );
            })}
          </div>
          <div className="mb-3 flex shrink-0 flex-wrap items-center gap-2">
            <input
              type="text"
              value={trainingSearch}
              onChange={(event) => setTrainingSearch(event.target.value)}
              placeholder="Search by name or subject"
              className="h-8 min-w-[12rem] flex-1 rounded-lg border border-foreground/10 bg-surface px-3 text-xs outline-none"
            />
            <select
              value={trainingSort}
              onChange={(event) => setTrainingSort(event.target.value as typeof trainingSort)}
              className="h-8 rounded-lg border border-foreground/10 bg-surface px-2 text-xs font-semibold outline-none"
              aria-label="Sort candidates"
            >
              <option value="recent">Recently updated</option>
              <option value="progress">Most lessons</option>
              <option value="average">Highest average</option>
              <option value="name">Name (A–Z)</option>
            </select>
          </div>
          <div className="min-h-0 flex-1 overflow-x-auto rounded-lg border border-foreground/8">
            <table className="h-full w-full min-w-[640px] table-fixed text-left">
              <thead className="bg-surface shadow-[0_1px_0_hsl(var(--foreground)/0.08)]">
                <tr className="border-b border-foreground/5">
                  {["Candidate", "Progress", "Average", "Last evaluated", ""].map((heading) => (
                    <th key={heading} className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {trainingRows.length ? (
                  pagedTrainingRows.map((candidate) => {
                    const meta = trainingMeta(candidate);
                    return (
                      <tr
                        key={asNumber(candidate.id)}
                        onClick={() => setDetailCandidateId(asNumber(candidate.id))}
                        className="cursor-pointer border-b border-foreground/5 hover:bg-muted/50"
                      >
                        <td className="px-3 py-2.5">
                          <div className="flex items-center gap-2">
                            <span className="block text-sm font-bold">{asString(candidate.full_name)}</span>
                            {meta.readyToPass ? (
                              <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-[9px] font-bold text-emerald-700">Ready</span>
                            ) : null}
                            {meta.stale ? (
                              <span className="rounded bg-amber-50 px-1.5 py-0.5 text-[9px] font-bold text-amber-700">Stalled</span>
                            ) : null}
                          </div>
                          <span className="text-xs text-muted-foreground">{asString(candidate.subject) || "Subject not set"}</span>
                        </td>
                        <td className="px-3 py-2.5">
                          <div className="flex items-center gap-2">
                            <div className="h-1.5 w-20 overflow-hidden rounded-full bg-muted">
                              <div className="h-full rounded-full bg-primary" style={{ width: `${meta.progress}%` }} />
                            </div>
                            <span className="text-[11px] font-semibold text-muted-foreground">
                              {meta.lessonCount}/{TRAINING_TARGET_LESSONS}
                            </span>
                          </div>
                        </td>
                        <td className="px-3 py-2.5 text-xs font-semibold">
                          {meta.average ? `${meta.average.toFixed(1)}/10` : "—"}
                        </td>
                        <td className="px-3 py-2.5 text-xs text-muted-foreground">
                          {meta.sinceLast === null ? "—" : meta.sinceLast === 0 ? "Today" : `${meta.sinceLast}d ago`}
                        </td>
                        <td className="px-3 py-2.5 text-right">
                          <span className="text-[11px] font-bold text-info">Open</span>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={5} className="px-3 py-8 text-center">
                      <p className="text-sm font-bold">
                        {trainingFilter === "rejected"
                          ? "No rejected candidates"
                          : trainingFilter === "passed"
                            ? "No candidates awaiting decision yet"
                            : "No candidates in training"}
                      </p>
                      <p className="mt-1 text-xs leading-5 text-muted-foreground">
                        {trainingFilter === "in_training"
                          ? "Candidates appear here once they pass the Math Test in the hiring pipeline."
                          : "Nothing to show for this filter yet."}
                      </p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <PaginationControls
            page={effectiveTrainingPage}
            totalPages={trainingTotalPages}
            onPageChange={setTrainingPage}
            label={`Showing ${pagedTrainingRows.length} of ${trainingRows.length} candidates`}
          />
        </ChartCard>
      ) : null}

      {activeTab === "active" ? (
        <ChartCard
          title="Active Teachers"
          subtitle={`${teachers.length} assigned`}
          icon={<Users className="h-4 w-4 text-info" />}
          className="flex min-h-0 flex-1 flex-col"
          bodyClassName="flex min-h-0 flex-1 flex-col"
        >
          <div className="min-h-0 flex-1 overflow-x-auto rounded-lg border border-foreground/8">
            <table className="h-full w-full min-w-[920px] table-fixed text-left">
              <thead className="bg-surface shadow-[0_1px_0_hsl(var(--foreground)/0.08)]">
                <tr className="border-b border-foreground/5">
                  {["Teacher", "Rank", "Progress", "Pay Rate", "Assigned Group", "Actions"].map((heading) => (
                    <th key={heading} className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {teachers.length ? (
                  pagedTeachers.map((teacher) => (
                    <tr key={asNumber(teacher.id)} className="border-b border-foreground/5">
                      <td className="px-3 py-2.5">
                        <span className="block text-sm font-bold">{asString(teacher.full_name)}</span>
                        <span className="text-xs text-muted-foreground">ID {asNumber(teacher.id)}</span>
                      </td>
                      <td className="px-3 py-2.5">
                        <span className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-[11px] font-bold text-emerald-700">
                          {teacherCategoryLabel(teacher.category)}
                        </span>
                        <span className="mt-1 block text-[11px] font-semibold text-muted-foreground">
                          Sem {asString(teacher.semester_stage) || "1-2"} · Score {asString(teacher.performance_score) || "7"}
                        </span>
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 w-20 overflow-hidden rounded-full bg-muted">
                            <div
                              className="h-full rounded-full bg-primary"
                              style={{ width: `${Math.min(100, Math.round((asNumber(teacher.supervised_lessons) / 120) * 100))}%` }}
                            />
                          </div>
                          <span className="text-[11px] font-semibold text-muted-foreground">
                            {asNumber(teacher.supervised_lessons)}/120
                          </span>
                        </div>
                      </td>
                      <td className="px-3 py-2.5 text-xs">{asString(teacher.pay_rate) || "-"}</td>
                      <td className="px-3 py-2.5 text-xs font-semibold">
                        {asString(teacher.assigned_group) || "-"}
                        {asString(teacher.login) ? (
                          <span className="mt-1 block text-[10px] font-normal text-muted-foreground">
                            Login {asString(teacher.login)} · Pass {asString(teacher.password) || "—"}
                          </span>
                        ) : null}
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-2">
                          <a
                            href={routes.adminTeacherEdit(asNumber(teacher.id), currentSchool)}
                            className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted"
                            aria-label={`Edit ${asString(teacher.full_name)}`}
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </a>
                          <button
                            type="button"
                            onClick={() => deleteTeacher(asNumber(teacher.id), asString(teacher.full_name))}
                            className="flex h-8 w-8 items-center justify-center rounded-lg text-destructive hover:bg-destructive/10"
                            aria-label={`Delete ${asString(teacher.full_name)}`}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="px-3 py-6 text-center text-sm text-muted-foreground">
                      No active teachers yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <PaginationControls
            page={effectiveTeacherPage}
            totalPages={teacherTotalPages}
            onPageChange={setTeacherPage}
            label={`Showing ${pagedTeachers.length} of ${teachers.length} teachers`}
          />
        </ChartCard>
      ) : null}
    </div>
  );
}
