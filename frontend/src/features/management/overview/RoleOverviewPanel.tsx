import { AlertCircle, AlertTriangle, BarChart3, BookOpen, Clock3, CreditCard, GraduationCap, MessageSquare, School, Trophy, Users } from "lucide-react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { asNumber, asString } from "@/features/managementTypes";
import { Candidate, candidateEvents, parseIsoMillis, candidateLastTouchedAt, candidateAgeDays, relativeDaysLabel, openTeacherCandidateView, roleStudentRows, supportComplaintRows, supportComplaintStatus, supportComplaintCategory, supportComplaintTitle, formatMoney, supportPaymentFollowUps, studentDashboardCards } from "./shared";
import { ClosedCandidatesOverviewCard, HrAttentionCard, RoleMetric } from "./cards";

function academyStatusLabel(value: unknown) {
  const labels: Record<string, string> = {
    new_academy_teacher: "New Academy Teacher",
    in_training: "In Academy",
    ready_for_evaluation: "Ready for Evaluation",
    needs_improvement: "Needs Improvement",
    ready_for_active_teacher: "Ready for Active Teacher",
    approved: "Approved",
    rejected: "Rejected",
    on_hold: "On Hold",
  };
  return labels[asString(value)] || asString(value) || "In Academy";
}

function formatDateTime(value: unknown) {
  const raw = asString(value);
  if (!raw) return "-";
  const parsed = Date.parse(raw);
  if (!Number.isFinite(parsed)) return raw.replace("T", " ").slice(0, 16);
  return new Intl.DateTimeFormat("en-GB", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(parsed));
}

function academyAssignments(teacher: Record<string, unknown>) {
  return Array.isArray(teacher.assignments) ? (teacher.assignments as Array<Record<string, unknown>>) : [];
}

function academyAssessments(teacher: Record<string, unknown>) {
  return Array.isArray(teacher.assessments) ? (teacher.assessments as Array<Record<string, unknown>>) : [];
}

function academyProgress(teacher: Record<string, unknown>) {
  const progress = teacher.progress && typeof teacher.progress === "object"
    ? (teacher.progress as Record<string, unknown>)
    : {};
  const assigned = asNumber(progress.assigned_count) || academyAssignments(teacher).length;
  const assessed = asNumber(progress.assessed_count);
  const passed = asNumber(progress.passed_count);
  const target = asNumber(progress.target_lessons) || assigned;
  const average = Number(progress.average_score);
  const latest = Number(progress.latest_score);
  return {
    assigned,
    assessed,
    passed,
    target,
    average: Number.isFinite(average) ? average : null,
    latest: Number.isFinite(latest) ? latest : null,
    nextAssignment: progress.next_assignment && typeof progress.next_assignment === "object"
      ? (progress.next_assignment as Record<string, unknown>)
      : null,
  };
}

function TeacherIdentityCard({ teacher }: { teacher: Record<string, unknown> | null }) {
  if (!teacher) return null;
  const score = asNumber(teacher.performance_score);
  return (
    <ChartCard title="Teacher Profile" subtitle="Previewing this teacher workspace" icon={<Users className="h-4 w-4 text-info" />}>
      <div className="grid gap-3 md:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-xl border border-foreground/8 bg-background p-4">
          <p className="text-lg font-bold">{asString(teacher.full_name) || "Teacher"}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            {asString(teacher.assigned_group) || "No group assigned"} · {asString(teacher.login) || "No login"}
          </p>
          <div className="mt-4 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
            <div className="rounded-lg bg-surface px-3 py-2">
              <p className="font-bold uppercase tracking-wide text-muted-foreground">Rank</p>
              <p className="mt-1 font-bold capitalize text-foreground">{asString(teacher.category).replace(/_/g, " ") || "-"}</p>
            </div>
            <div className="rounded-lg bg-surface px-3 py-2">
              <p className="font-bold uppercase tracking-wide text-muted-foreground">Semester</p>
              <p className="mt-1 font-bold text-foreground">{asString(teacher.semester_stage) || "-"}</p>
            </div>
            <div className="rounded-lg bg-surface px-3 py-2">
              <p className="font-bold uppercase tracking-wide text-muted-foreground">Score</p>
              <p className="mt-1 font-bold text-primary">{score ? score.toFixed(1) : "-"}</p>
            </div>
            <div className="rounded-lg bg-surface px-3 py-2">
              <p className="font-bold uppercase tracking-wide text-muted-foreground">Lessons</p>
              <p className="mt-1 font-bold text-foreground">{asNumber(teacher.supervised_lessons)}</p>
            </div>
          </div>
        </div>
        <div className="rounded-xl border border-emerald-100 bg-emerald-50 p-4 text-emerald-900">
          <p className="text-xs font-bold uppercase tracking-wide text-emerald-700">Active Teacher</p>
          <p className="mt-2 text-sm leading-6">
            This preview uses the selected teacher's assigned group, students, timetable, resources, and announcements.
          </p>
        </div>
      </div>
    </ChartCard>
  );
}

function AcademyTeacherPreview({ teacher }: { teacher: Record<string, unknown> }) {
  const assignments = academyAssignments(teacher);
  const assessments = academyAssessments(teacher).slice().reverse();
  const progress = academyProgress(teacher);
  const percent = progress.target ? Math.min(100, Math.round((progress.assessed / progress.target) * 100)) : 0;
  const login = asString(teacher.login);

  return (
    <div className="space-y-3">
      <ChartCard title="Teacher Academy Profile" subtitle="Teacher role preview for Academy teachers" icon={<GraduationCap className="h-4 w-4 text-info" />}>
        <div className="grid gap-3 xl:grid-cols-[1fr_0.8fr]">
          <div className="rounded-xl border border-foreground/8 bg-background p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-xl font-bold">{asString(teacher.full_name) || "Academy Teacher"}</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {asString(teacher.subject) || "Subject"} · {academyStatusLabel(teacher.academy_status)}
                </p>
              </div>
              <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-bold uppercase tracking-wide text-amber-700">
                Academy
              </span>
            </div>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-muted">
              <div className="h-full rounded-full bg-primary transition-[width] duration-300" style={{ width: `${percent}%` }} />
            </div>
            <div className="mt-4 grid gap-2 sm:grid-cols-2">
              <div className="rounded-xl border border-primary/10 bg-primary/5 px-3 py-2">
                <p className="text-[10px] font-black uppercase tracking-wide text-primary">Teacher account login</p>
                <p className="mt-1 truncate font-mono text-sm font-black text-foreground">{login || "Account not created"}</p>
              </div>
              <div className="rounded-xl border border-primary/10 bg-primary/5 px-3 py-2">
                <p className="text-[10px] font-black uppercase tracking-wide text-primary">Default password</p>
                <p className="mt-1 truncate font-mono text-sm font-black text-foreground">{login || "Account not created"}</p>
                <p className="mt-1 text-[10px] font-bold text-muted-foreground">Default password equals login.</p>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
              <RoleMetric label="Assigned" value={progress.assigned} detail="lessons" icon={<BookOpen className="h-4 w-4" />} tone="bg-sky-50" />
              <RoleMetric label="Assessed" value={progress.assessed} detail={`of ${progress.target}`} icon={<Clock3 className="h-4 w-4" />} tone="bg-violet-50" />
              <RoleMetric label="Passed" value={progress.passed} detail="accepted" icon={<Trophy className="h-4 w-4" />} tone="bg-emerald-50" />
              <RoleMetric label="Average" value={progress.average == null ? "-" : progress.average.toFixed(1)} detail="weighted" icon={<BarChart3 className="h-4 w-4" />} tone="bg-amber-50" />
            </div>
          </div>
          <div className="rounded-xl border border-foreground/8 bg-background p-4">
            <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Next Academy Lesson</p>
            {progress.nextAssignment ? (
              <div className="mt-3">
                <p className="text-base font-bold">{asString(progress.nextAssignment.lesson_number)}</p>
                <p className="mt-1 text-sm leading-5 text-muted-foreground">{asString(progress.nextAssignment.lesson_topic)}</p>
                <p className="mt-3 text-xs font-semibold text-muted-foreground">
                  {formatDateTime(progress.nextAssignment.session_datetime)} · {asString(progress.nextAssignment.evaluator_name) || "No evaluator"}
                </p>
              </div>
            ) : (
              <p className="mt-3 text-sm text-muted-foreground">No remaining lesson is waiting for assessment.</p>
            )}
          </div>
        </div>
      </ChartCard>

      <div className="grid gap-3 xl:grid-cols-[1.1fr_0.9fr]">
        <ChartCard title="Selected Academy Lessons" subtitle={`${assignments.length} curriculum lessons`} icon={<BookOpen className="h-4 w-4 text-info" />}>
          <div className="miniapp-table-scroll max-h-[28rem] rounded-lg border border-foreground/8">
            <div className="grid gap-0 divide-y divide-foreground/5 bg-background">
              {assignments.map((assignment) => (
                <div key={asNumber(assignment.id)} className="grid gap-2 px-3 py-2.5 sm:grid-cols-[3rem_1fr_auto]">
                  <span className="text-xs font-bold text-muted-foreground">{asNumber(assignment.sequence_no)}</span>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-bold">{asString(assignment.lesson_number)} · {asString(assignment.lesson_topic)}</p>
                    <p className="mt-0.5 line-clamp-2 text-[11px] leading-4 text-muted-foreground">{asString(assignment.specification_points) || "Guided lesson practice"}</p>
                  </div>
                  <span className="h-fit rounded-md bg-muted px-2 py-1 text-[10px] font-bold uppercase text-muted-foreground">
                    {asString(assignment.status) || "assigned"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </ChartCard>

        <ChartCard title="Assessment Reports" subtitle={`${assessments.length} saved`} icon={<Trophy className="h-4 w-4 text-info" />}>
          <div className="max-h-[28rem] space-y-2 overflow-y-auto pr-1">
            {assessments.length ? assessments.map((assessment) => (
              <div key={asNumber(assessment.id)} className="rounded-lg border border-foreground/8 bg-background p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-bold">{asString(assessment.lesson_number)} · {asString(assessment.lesson_topic)}</p>
                    <p className="mt-0.5 text-[11px] text-muted-foreground">{formatDateTime(assessment.assessment_datetime)}</p>
                  </div>
                  <span className="rounded-md bg-primary/10 px-2 py-1 text-xs font-bold text-primary">
                    {Number(assessment.weighted_overall_score || 0).toFixed(1)}
                  </span>
                </div>
                <p className="mt-2 line-clamp-3 text-xs leading-5 text-muted-foreground">
                  {asString(assessment.areas_for_improvement) || asString(assessment.final_recommendation) || asString(assessment.strengths) || "No notes."}
                </p>
              </div>
            )) : (
              <div className="rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-8 text-center">
                <p className="text-sm font-bold text-muted-foreground">No assessment reports yet.</p>
              </div>
            )}
          </div>
        </ChartCard>
      </div>
    </div>
  );
}

export function RoleOverviewPanel({ state }: { state: any }) {
  const mode = asString(state.adminMode).toLowerCase();
  const students = roleStudentRows(state);
  const teachers = Array.isArray(state.teachers) ? (state.teachers as Array<Record<string, unknown>>) : [];
  const candidates = Array.isArray(state.props?.adminTeacherCandidates)
    ? (state.props.adminTeacherCandidates as Array<Record<string, unknown>>)
    : [];
  const resources = Array.isArray(state.resourcesList) ? (state.resourcesList as Array<Record<string, unknown>>) : [];
  const announcements = Array.isArray(state.props?.adminAnnouncements)
    ? (state.props.adminAnnouncements as Array<Record<string, unknown>>)
    : [];
  const groups = Array.isArray(state.props?.adminAcademicGroups)
    ? (state.props.adminAcademicGroups as Array<Record<string, unknown>>)
    : [];
  const currentSchool = asString(state.currentSchool) || "all";
  const activeStudents = students.filter((student) => asString(student.last_seen_at)).length;
  const activePipelineCandidates = candidates.filter((candidate) => {
    const status = asString(candidate.status) || "new";
    return !["rejected", "withdrawn", "hired"].includes(status);
  });
  const closedCandidates = candidates.filter((candidate) => {
    const status = asString(candidate.status) || "new";
    return ["rejected", "withdrawn"].includes(status);
  });
  const hiredCandidates = candidates.filter((candidate) => asString(candidate.status) === "hired");
  const inTraining = candidates.filter((candidate) => asString(candidate.status) === "training_ready").length;
  const awaitingDecision = candidates.filter((candidate) => asString(candidate.status) === "training_passed").length;
  const newCandidates = candidates.filter((candidate) => asString(candidate.status) === "new").length;
  const interviewCandidates = candidates.filter((candidate) => asString(candidate.status) === "interview").length;
  const mathTestCandidates = candidates.filter((candidate) => asString(candidate.status) === "math_test").length;
  const hiresThisMonth = hiredCandidates.filter((candidate) => {
    const parsed = parseIsoMillis(candidateLastTouchedAt(candidate));
    if (parsed == null) return false;
    const date = new Date(parsed);
    const now = new Date();
    return date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth();
  }).length;
  const closedDecisionCount = closedCandidates.length + hiredCandidates.length;
  const rejectionRate = closedDecisionCount ? Math.round((closedCandidates.length / closedDecisionCount) * 100) : 0;

  const urgentItems = activePipelineCandidates
    .map((candidate) => {
      const status = asString(candidate.status) || "new";
      const ageDays = candidateAgeDays(candidate);
      const evaluations = candidateEvents(candidate).filter((event) => asString(event.event_type) === "training_evaluation");
      if (status === "training_passed" && (ageDays ?? 0) >= 3) {
        return {
          candidateId: asNumber(candidate.id),
          fullName: asString(candidate.full_name) || "Candidate",
          title: "Final decision overdue",
          detail: `${relativeDaysLabel(ageDays)} since sent for final review`,
          tone: "bad" as const,
          priority: 5,
          tab: "training" as const,
          filter: "passed" as const,
        };
      }
      if (status === "training_ready" && !evaluations.length && (ageDays ?? 0) >= 2) {
        return {
          candidateId: asNumber(candidate.id),
          fullName: asString(candidate.full_name) || "Candidate",
          title: "Practice needs first evaluation",
          detail: `${relativeDaysLabel(ageDays)} in practice with no lesson review`,
          tone: "bad" as const,
          priority: 4,
          tab: "training" as const,
          filter: "in_training" as const,
        };
      }
      if (status === "training_ready" && (ageDays ?? 0) >= 5) {
        return {
          candidateId: asNumber(candidate.id),
          fullName: asString(candidate.full_name) || "Candidate",
          title: "Practice looks stalled",
          detail: `${relativeDaysLabel(ageDays)} since the last practice activity`,
          tone: "warn" as const,
          priority: 3,
          tab: "training" as const,
          filter: "in_training" as const,
        };
      }
      if (status === "math_test" && (ageDays ?? 0) >= 2) {
        return {
          candidateId: asNumber(candidate.id),
          fullName: asString(candidate.full_name) || "Candidate",
          title: "Math test pending follow-up",
          detail: `${relativeDaysLabel(ageDays)} waiting in the test stage`,
          tone: "warn" as const,
          priority: 2,
          tab: "hiring" as const,
        };
      }
      if (status === "interview" && (ageDays ?? 0) >= 2) {
        return {
          candidateId: asNumber(candidate.id),
          fullName: asString(candidate.full_name) || "Candidate",
          title: "Interview queue is aging",
          detail: `${relativeDaysLabel(ageDays)} in interview stage`,
          tone: "info" as const,
          priority: 1,
          tab: "hiring" as const,
        };
      }
      if (status === "new" && (ageDays ?? 0) >= 1) {
        return {
          candidateId: asNumber(candidate.id),
          fullName: asString(candidate.full_name) || "Candidate",
          title: "Needs first screening",
          detail: `${relativeDaysLabel(ageDays)} since application was added`,
          tone: "info" as const,
          priority: 0,
          tab: "hiring" as const,
        };
      }
      return null;
    })
    .filter((item): item is NonNullable<typeof item> => item !== null)
    .sort((left, right) => {
      if (left.priority !== right.priority) return right.priority - left.priority;
      return right.candidateId - left.candidateId;
    })
    .slice(0, 4);

  const pipelineSnapshotStages = [
    { key: "new", label: "New", count: newCandidates, tone: "bg-sky-500", tab: "hiring" as const },
    {
      key: "interview_test",
      label: "Interview / Test",
      count: interviewCandidates + mathTestCandidates,
      tone: "bg-amber-500",
      tab: "hiring" as const,
    },
    {
      key: "training_ready",
      label: "Practice",
      count: inTraining,
      tone: "bg-emerald-500",
      tab: "training" as const,
      filter: "in_training" as const,
    },
    {
      key: "training_passed",
      label: "Review",
      count: awaitingDecision,
      tone: "bg-violet-500",
      tab: "training" as const,
      filter: "passed" as const,
    },
  ];
  const openPipelineTotal = Math.max(
    1,
    pipelineSnapshotStages.reduce((sum, stage) => sum + stage.count, 0),
  );

  function openRejectedQueue() {
    openTeacherCandidateView(state.switchAdminTab, {
      tab: "training",
      filter: "rejected",
    });
  }

  if (mode === "student" || mode === "parent") {
    return (
      <div className="space-y-3">
        <div className="grid gap-2 md:grid-cols-3">
          <RoleMetric label="Students" value={students.length} detail="dashboard access" icon={<Users className="h-4 w-4" />} tone="bg-sky-50" />
          <RoleMetric label="Resources" value={resources.length} detail="available learning materials" icon={<BookOpen className="h-4 w-4" />} tone="bg-emerald-50" />
          <RoleMetric label="Announcements" value={announcements.length} detail="school updates" icon={<AlertCircle className="h-4 w-4" />} tone="bg-amber-50" />
        </div>
        {studentDashboardCards({
          students,
          currentSchool,
          title: mode === "parent" ? "Student Dashboard" : "My Dashboard",
          emptyText: "No student dashboard is available yet.",
        })}
      </div>
    );
  }

  if (mode === "teacher" && state.academyTeacherPreview) {
    return <AcademyTeacherPreview teacher={state.academyTeacherPreview as Record<string, unknown>} />;
  }

  if (mode === "hr_manager") {
    return (
      <div className="space-y-3">
        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
          <RoleMetric label="New" value={newCandidates} detail="fresh applications" icon={<Users className="h-4 w-4" />} tone="bg-sky-50" />
          <RoleMetric label="Practice" value={inTraining} detail="trainees in lessons" icon={<GraduationCap className="h-4 w-4" />} tone="bg-emerald-50" />
          <RoleMetric label="Review" value={awaitingDecision} detail="awaiting final decision" icon={<Trophy className="h-4 w-4" />} tone="bg-violet-50" />
          <RoleMetric label="Overdue" value={urgentItems.length} detail="need attention now" icon={<Clock3 className="h-4 w-4" />} tone={urgentItems.length ? "bg-rose-50" : "bg-slate-50"} />
        </div>
        <div className="grid items-stretch gap-3 xl:grid-cols-[1.1fr_0.9fr]">
          <HrAttentionCard
            urgentItems={urgentItems}
            onOpenItem={(item) =>
              openTeacherCandidateView(state.switchAdminTab, {
                tab: item.tab,
                filter: item.filter,
                candidateId: item.candidateId,
              })
            }
          />
          <ChartCard title="Pipeline Snapshot" subtitle="Open queue only" icon={<BarChart3 className="h-4 w-4 text-info" />}>
            <div className="flex min-h-[22rem] flex-col rounded-lg border border-foreground/8 bg-background p-3">
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs font-semibold text-muted-foreground">Stage distribution</p>
                <span className="text-[11px] font-semibold text-muted-foreground">
                  {activePipelineCandidates.length} open
                </span>
              </div>
              <div className="mt-3 flex h-3 overflow-hidden rounded-full bg-muted">
                {pipelineSnapshotStages.map((stage) => {
                  const percent = Math.round((stage.count / openPipelineTotal) * 100);
                  return (
                    <button
                      key={`${stage.key}-snapshot`}
                      type="button"
                      onClick={() => openTeacherCandidateView(state.switchAdminTab, stage)}
                      className={`${stage.tone} h-full transition-opacity hover:opacity-85`}
                      style={{ width: `${percent}%` }}
                      title={`${stage.label}: ${stage.count}`}
                    />
                  );
                })}
              </div>
              <div className="mt-4 space-y-2">
                {pipelineSnapshotStages.map((stage) => {
                  const percent = Math.round((stage.count / openPipelineTotal) * 100);
                  return (
                    <button
                      key={stage.key}
                      type="button"
                      onClick={() => openTeacherCandidateView(state.switchAdminTab, stage)}
                      className="flex w-full items-center gap-3 rounded-md px-2 py-2.5 text-left transition-colors hover:bg-surface"
                    >
                      <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${stage.tone}`} />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-sm font-bold">{stage.label}</span>
                          <span className="text-base font-bold tabular-nums">{stage.count}</span>
                        </div>
                        <p className="mt-1 text-[11px] text-muted-foreground">{percent}% of open queue</p>
                      </div>
                    </button>
                  );
                })}
              </div>
              <div className="mt-auto grid gap-2 border-t border-foreground/8 pt-3 sm:grid-cols-3">
                {[
                  {
                    label: "Open",
                    value: activePipelineCandidates.length,
                    detail: "not yet closed",
                    tone: "text-sky-700",
                  },
                  {
                    label: "Hired",
                    value: hiresThisMonth,
                    detail: "this month",
                    tone: "text-emerald-700",
                  },
                  {
                    label: "Reject Rate",
                    value: `${rejectionRate}%`,
                    detail: `${closedDecisionCount} resolved`,
                    tone:
                      rejectionRate >= 60
                        ? "text-rose-700"
                        : rejectionRate >= 35
                          ? "text-amber-700"
                          : "text-emerald-700",
                  },
                ].map((item) => (
                  <div key={item.label} className="rounded-md bg-surface px-3 py-2">
                    <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">{item.label}</p>
                    <div className="mt-1 flex items-end justify-between gap-2">
                      <p className={`text-lg font-bold leading-none ${item.tone}`}>{item.value}</p>
                      <p className="text-[11px] font-semibold text-muted-foreground">{item.detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </ChartCard>
        </div>
        <ClosedCandidatesOverviewCard candidates={candidates} onOpenRejected={openRejectedQueue} />
      </div>
    );
  }

  if (mode === "academic_director") {
    const redZones = Array.isArray(state.props?.adminGroupZones?.red) ? state.props.adminGroupZones.red : [];
    const yellowZones = Array.isArray(state.props?.adminGroupZones?.yellow) ? state.props.adminGroupZones.yellow : [];
    const atRiskGroups = [...redZones, ...yellowZones];
    const totalTeachers = state.quickStats?.total_teachers ?? teachers.length;
    const totalStudents = state.quickStats?.total_students ?? students.length;

    return (
      <div className="space-y-3">
        <div className="grid gap-2 md:grid-cols-4">
          <button type="button" onClick={() => state.switchAdminTab("teachers")} className="text-left">
            <RoleMetric label="Teachers" value={totalTeachers} detail="active teaching staff" icon={<Users className="h-4 w-4" />} tone="bg-sky-50" />
          </button>
          <button type="button" onClick={() => state.switchAdminTab("groups")} className="text-left">
            <RoleMetric label="Groups" value={groups.length} detail="active class groups" icon={<School className="h-4 w-4" />} tone="bg-emerald-50" />
          </button>
          <button type="button" onClick={() => state.switchAdminTab("gradebook")} className="text-left">
            <RoleMetric label="Students" value={totalStudents} detail="enrolled students" icon={<GraduationCap className="h-4 w-4" />} tone="bg-amber-50" />
          </button>
          <button type="button" onClick={() => state.switchAdminTab("gradebook")} className="text-left">
            <RoleMetric label="At-Risk Groups" value={redZones.length} detail="AAP average < 5.0" icon={<AlertCircle className="h-4 w-4" />} tone={redZones.length ? "bg-rose-50" : "bg-slate-50"} />
          </button>
        </div>

        <div className="grid gap-3 xl:grid-cols-[1.1fr_0.9fr]">
          <ChartCard title="Group Academic Risk" subtitle={`${atRiskGroups.length} groups in Yellow/Red zones`} icon={<AlertCircle className="h-4 w-4 text-info" />}>
            {atRiskGroups.length ? (
              <div className="miniapp-table-scroll max-h-[22rem] rounded-lg border border-foreground/10">
                <table className="w-full text-left text-xs">
                  <thead className="sticky top-0 bg-surface shadow-[0_1px_0_hsl(var(--foreground)/0.08)]">
                    <tr className="border-b border-foreground/5">
                      <th className="px-3 py-2 font-bold uppercase tracking-wide text-muted-foreground">Group</th>
                      <th className="px-3 py-2 font-bold uppercase tracking-wide text-muted-foreground">Subject</th>
                      <th className="px-3 py-2 font-bold uppercase tracking-wide text-muted-foreground">School</th>
                      <th className="px-3 py-2 text-center font-bold uppercase tracking-wide text-muted-foreground">AAP</th>
                      <th className="px-3 py-2 text-center font-bold uppercase tracking-wide text-muted-foreground">AR</th>
                      <th className="px-3 py-2 font-bold uppercase tracking-wide text-muted-foreground">Zone</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-foreground/5 bg-background">
                    {atRiskGroups.map((group, idx) => {
                      const aap = asNumber(group.aap);
                      const isRed = aap < 5;
                      return (
                        <tr key={idx} className="hover:bg-muted/50">
                          <td className="px-3 py-2.5 font-semibold">{asString(group.group_name)}</td>
                          <td className="px-3 py-2.5 text-muted-foreground">{asString(group.subject_name)}</td>
                          <td className="px-3 py-2.5 text-muted-foreground">{asString(group.school_name)}</td>
                          <td className="px-3 py-2.5 text-center font-bold">{aap.toFixed(1)}</td>
                          <td className="px-3 py-2.5 text-center font-bold">{asNumber(group.ar).toFixed(0)}%</td>
                          <td className="px-3 py-2.5">
                            <span className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-bold uppercase ${
                              isRed ? "bg-rose-50 text-rose-700 border border-rose-200" : "bg-amber-50 text-amber-700 border border-amber-200"
                            }`}>
                              {isRed ? "Red" : "Yellow"}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-8 text-center">
                <p className="text-sm font-bold">All groups are in the Green zone! Excellent health.</p>
              </div>
            )}
          </ChartCard>

          <ChartCard title="Academic Quality / Teacher Performance" subtitle={`${teachers.length} teachers`} icon={<Trophy className="h-4 w-4 text-info" />}>
            {teachers.length ? (
              <div className="miniapp-table-scroll max-h-[22rem] rounded-lg border border-foreground/10">
                <table className="w-full text-left text-xs">
                  <thead className="sticky top-0 bg-surface shadow-[0_1px_0_hsl(var(--foreground)/0.08)]">
                    <tr className="border-b border-foreground/5">
                      <th className="px-3 py-2 font-bold uppercase tracking-wide text-muted-foreground">Teacher</th>
                      <th className="px-3 py-2 font-bold uppercase tracking-wide text-muted-foreground">Group</th>
                      <th className="px-3 py-2 font-bold uppercase tracking-wide text-muted-foreground">Category</th>
                      <th className="px-3 py-2 text-center font-bold uppercase tracking-wide text-muted-foreground">Score</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-foreground/5 bg-background">
                    {teachers.map((teacher, idx) => {
                      const score = asNumber(teacher.performance_score);
                      return (
                        <tr key={idx} className="hover:bg-muted/50">
                          <td className="px-3 py-2.5 font-semibold">{asString(teacher.full_name)}</td>
                          <td className="px-3 py-2.5 text-muted-foreground">{asString(teacher.assigned_group)}</td>
                          <td className="px-3 py-2.5 capitalize text-muted-foreground">{asString(teacher.category)}</td>
                          <td className="px-3 py-2.5 text-center font-bold text-primary">{score.toFixed(1)}/10</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-8 text-center">
                <p className="text-sm font-bold">No teachers registered yet.</p>
              </div>
            )}
          </ChartCard>
        </div>
      </div>
    );
  }

  if (mode === "customer_support") {
    const complaints = supportComplaintRows(state);
    const newComplaints = complaints.filter((item) => supportComplaintStatus(item.status) === "new");
    const escalatedComplaints = complaints.filter((item) => supportComplaintStatus(item.status) === "escalated");
    const openComplaints = complaints.filter((item) => supportComplaintStatus(item.status) !== "resolved");
    const paymentFollowUps = supportPaymentFollowUps(state);
    const unresolvedPaymentTotal = paymentFollowUps.reduce((sum, item) => sum + item.total, 0);
    return (
      <div className="space-y-3">
        <div className="grid gap-2 md:grid-cols-4">
          <button type="button" onClick={() => state.switchAdminTab("complaints")} className="text-left">
            <RoleMetric label="New Complaints" value={newComplaints.length} detail="need first reply" icon={<AlertCircle className="h-4 w-4" />} tone="bg-amber-50" />
          </button>
          <button type="button" onClick={() => state.switchAdminTab("complaints")} className="text-left">
            <RoleMetric label="Escalated" value={escalatedComplaints.length} detail="CEO attention" icon={<AlertTriangle className="h-4 w-4" />} tone="bg-rose-50" />
          </button>
          <button type="button" onClick={() => state.switchAdminTab("payments")} className="text-left">
            <RoleMetric label="Unresolved Payments" value={paymentFollowUps.length} detail={formatMoney(unresolvedPaymentTotal)} icon={<CreditCard className="h-4 w-4" />} tone="bg-sky-50" />
          </button>
          <button type="button" onClick={() => state.switchAdminTab("chat")} className="text-left">
            <RoleMetric label="Chats" value="Open" detail="parent conversations" icon={<MessageSquare className="h-4 w-4" />} tone="bg-violet-50" />
          </button>
        </div>

        <div className="grid gap-3 xl:grid-cols-[1.1fr_0.9fr]">
          <ChartCard title="Complaint Queue" subtitle={`${openComplaints.length} open`} icon={<MessageSquare className="h-4 w-4 text-info" />}>
            {openComplaints.length ? (
              <div className="space-y-2">
                {openComplaints.slice(0, 5).map((complaint) => (
                  <button
                    key={asNumber(complaint.id)}
                    type="button"
                    onClick={() => state.switchAdminTab("complaints")}
                    className="w-full rounded-lg border border-foreground/10 bg-background px-3 py-3 text-left transition-colors hover:bg-muted"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="truncate text-sm font-bold">{supportComplaintTitle(complaint)}</p>
                      <span className="rounded-md bg-muted px-2 py-1 text-[11px] font-bold">
                        {supportComplaintStatus(complaint.status) === "escalated" ? "Escalated" : supportComplaintStatus(complaint.status) === "in_progress" ? "In Progress" : "New"}
                      </span>
                    </div>
                    <p className="mt-1 truncate text-xs text-muted-foreground">
                      {asString(complaint.parent_login) || "Parent"} · {asString(complaint.student_name) || "Student"} · {supportComplaintCategory(complaint.category)}
                    </p>
                    <p className="mt-2 line-clamp-2 text-xs leading-5 text-foreground/75">{asString(complaint.message)}</p>
                  </button>
                ))}
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-8 text-center">
                <p className="text-sm font-bold">No open complaints right now.</p>
              </div>
            )}
          </ChartCard>

          <ChartCard title="Payment Follow-Up" subtitle={`${paymentFollowUps.length} families`} icon={<CreditCard className="h-4 w-4 text-info" />}>
            {paymentFollowUps.length ? (
              <div className="space-y-2">
                {paymentFollowUps.map((item) => (
                  <button
                    key={`${item.parent}-${item.studentRowId}`}
                    type="button"
                    onClick={() => state.switchAdminTab("payments")}
                    className="w-full rounded-lg border border-foreground/10 bg-background px-3 py-3 text-left transition-colors hover:bg-muted"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-bold">{item.parent}</p>
                        <p className="mt-1 truncate text-xs text-muted-foreground">{item.child}</p>
                      </div>
                      <p className="shrink-0 text-sm font-bold">{formatMoney(item.total, item.currency)}</p>
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-8 text-center">
                <p className="text-sm font-bold">No unresolved payments right now.</p>
              </div>
            )}
          </ChartCard>
        </div>
      </div>
    );
  }

  const activeTeacher = teachers[0] || null;

  return (
    <div className="space-y-3">
      <TeacherIdentityCard teacher={activeTeacher} />
      <div className="grid gap-2 md:grid-cols-4">
        <RoleMetric label="My Students" value={students.length} detail="visible student records" icon={<Users className="h-4 w-4" />} tone="bg-sky-50" />
        <RoleMetric label="Groups" value={groups.length} detail="class groups" icon={<School className="h-4 w-4" />} tone="bg-emerald-50" />
        <RoleMetric label="Resources" value={resources.length} detail="teaching materials" icon={<BookOpen className="h-4 w-4" />} tone="bg-amber-50" />
        <RoleMetric label="Announcements" value={announcements.length} detail="class updates" icon={<AlertCircle className="h-4 w-4" />} tone="bg-violet-50" />
      </div>
      {studentDashboardCards({
        students,
        currentSchool,
        title: "Class Student Dashboards",
        emptyText: "No students are assigned to this teacher view yet.",
      })}
    </div>
  );
}
