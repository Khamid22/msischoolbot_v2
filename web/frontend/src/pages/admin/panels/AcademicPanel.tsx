import { useState, useEffect, useMemo, useRef } from "react";
import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";
import {
  ArrowRight,
  BookMarked,
  ChevronLeft,
  Layers,
  Plus,
  RotateCcw,
  Search,
  Users,
  UserX,
  X,
} from "lucide-react";
import { ChartCard } from "@/components/ChartCard";
import { routes } from "@/lib/routes";
import { asNumber, asString, AdminTab } from "../shared";

// ─── Form helpers ─────────────────────────────────────────────────────────────

function FieldLabel({ children }: { children: string }) {
  return (
    <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
      {children}
    </span>
  );
}

function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className="w-full rounded-lg border border-foreground/10 bg-surface px-3 py-2 text-sm outline-none focus:border-foreground/30"
    />
  );
}

function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className="w-full rounded-lg border border-foreground/10 bg-surface px-3 py-2 text-sm outline-none focus:border-foreground/30"
    />
  );
}

function Pill({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex h-6 items-center rounded-md border border-foreground/10 bg-muted px-2 text-xs font-semibold text-muted-foreground">
      {children}
    </span>
  );
}

function MiniMetric({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-lg border border-foreground/8 bg-background px-3 py-2">
      <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground">
        {icon}
        {label}
      </div>
      <p className="mt-1 text-lg font-bold leading-none">{value}</p>
    </div>
  );
}

const subjectSwatches = [
  "bg-primary",
  "bg-info",
  "bg-emerald-500",
  "bg-amber-500",
  "bg-rose-500",
  "bg-cyan-500",
  "bg-violet-500",
] as const;

function subjectSwatch(value: string) {
  const seed = Array.from(value || "group").reduce((sum, char) => sum + char.charCodeAt(0), 0);
  return subjectSwatches[seed % subjectSwatches.length];
}

// ─── Gradebook types ──────────────────────────────────────────────────────────

type Lesson = {
  id: number;
  lessonNumber: string;
  topic: string;
  date: string;
  order: number;
};

type Enrollment = {
  enrollmentId: number;
  publicDashboardId?: number;
  fullName: string;
  averageGrade: number;
  coins: number;
  active?: boolean;
  status?: string;
  disqualificationReason?: string;
  disqualifiedAt?: string;
  attendance: Record<string, string>;
  homework: Record<string, number>;
};

type GradebookData = {
  group: { id: number; name: string; subjectName: string; schoolCode: string };
  lessons: Lesson[];
  enrollments: Enrollment[];
  allEnrollments?: Enrollment[];
};

type ActiveCell = {
  enrollmentId: number;
  lesson: Lesson;
  kind: "att" | "hw";
  anchorRect: DOMRect;
};

const ATT_VALUES = ["present", "absent", "justified"] as const;
type AttValue = (typeof ATT_VALUES)[number] | "";

function attLabel(v: string) {
  if (v === "present") return "P";
  if (v === "absent") return "A";
  if (v === "justified") return "J";
  return "";
}

function attCls(v: string) {
  if (v === "present") return "bg-emerald-500 text-white";
  if (v === "absent") return "bg-red-500 text-white";
  if (v === "justified") return "bg-amber-400 text-white";
  return "";
}

function EnrollmentList({
  title,
  icon,
  rows,
  emptyText,
  actionLabel,
  actionIcon,
  actionTone,
  savingId,
  onAction,
}: {
  title: string;
  icon: ReactNode;
  rows: Enrollment[];
  emptyText: string;
  actionLabel: string;
  actionIcon: ReactNode;
  actionTone: "danger" | "neutral";
  savingId: number | null;
  onAction: (enrollmentId: number) => void;
}) {
  return (
    <div className="rounded-lg border border-foreground/8 bg-background">
      <div className="flex items-center justify-between border-b border-foreground/8 px-3 py-2">
        <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-muted-foreground">
          {icon}
          {title}
        </span>
        <span className="text-xs font-semibold text-muted-foreground">{rows.length}</span>
      </div>
      <div className="max-h-64 overflow-y-auto p-2">
        {rows.length === 0 ? (
          <p className="px-2 py-4 text-sm text-muted-foreground">{emptyText}</p>
        ) : (
          <div className="space-y-1.5">
            {rows.map((row) => (
              <div
                key={row.enrollmentId}
                className="flex items-center justify-between gap-3 rounded-lg border border-foreground/5 bg-surface px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold">{row.fullName}</p>
                  <p className="mt-0.5 text-[11px] text-muted-foreground">
                    ID {row.publicDashboardId || row.enrollmentId}
                    {row.disqualificationReason ? ` · ${row.disqualificationReason}` : ""}
                  </p>
                </div>
                <button
                  type="button"
                  disabled={savingId === row.enrollmentId}
                  onClick={() => onAction(row.enrollmentId)}
                  className={`inline-flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-bold disabled:opacity-50 ${
                    actionTone === "danger"
                      ? "bg-red-50 text-red-700 hover:bg-red-100"
                      : "bg-muted text-muted-foreground hover:bg-foreground/10"
                  }`}
                >
                  {actionIcon}
                  {savingId === row.enrollmentId ? "Saving" : actionLabel}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Gradebook view ───────────────────────────────────────────────────────────

function GroupGradebook({
  groupId,
  csrf,
  onClose,
}: {
  groupId: number;
  csrf: string;
  onClose: () => void;
}) {
  const [data, setData] = useState<GradebookData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [active, setActive] = useState<ActiveCell | null>(null);
  const [hwInput, setHwInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [enrollmentSearch, setEnrollmentSearch] = useState("");
  const [statusSavingId, setStatusSavingId] = useState<number | null>(null);
  const popRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    load(groupId, controller.signal);
    return () => controller.abort();
  }, [groupId]);

  useEffect(() => {
    if (!active) return;
    const handler = (e: MouseEvent) => {
      if (popRef.current && !popRef.current.contains(e.target as Node)) close();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [active]);

  async function load(id: number, signal?: AbortSignal) {
    setLoading(true);
    setError("");
    setActive(null);
    try {
      const res = await fetch(routes.adminAcademicGradebookApi(id), { signal });
      const json = await res.json();
      if (json.ok) setData(json as GradebookData);
      else setError(json.message || "Failed to load.");
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") return;
      setError("Network error.");
    } finally {
      setLoading(false);
    }
  }

  function openCell(
    e: React.MouseEvent<HTMLButtonElement>,
    enrollmentId: number,
    lesson: Lesson,
    kind: "att" | "hw",
    currentHw: number | undefined,
  ) {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    setActive({ enrollmentId, lesson, kind, anchorRect: rect });
    setHwInput(currentHw !== undefined ? String(currentHw) : "");
  }

  function close() {
    setActive(null);
    setSaving(false);
  }

  async function saveAtt(status: AttValue) {
    if (!active || saving) return;
    setSaving(true);
    try {
      await fetch(routes.adminAcademicAttendanceApi, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
        body: JSON.stringify({
          enrollment_id: active.enrollmentId,
          lesson_label: active.lesson.lessonNumber,
          status: status || "present",
          topic: active.lesson.topic,
          lesson_date: active.lesson.date,
          attendance_type: "regular",
        }),
      });
      patchAtt(active.enrollmentId, active.lesson.lessonNumber, status);
      close();
    } finally {
      setSaving(false);
    }
  }

  async function saveHw() {
    if (!active || saving || hwInput === "") return;
    const score = parseFloat(hwInput);
    if (isNaN(score)) return;
    setSaving(true);
    try {
      await fetch(routes.adminAcademicHomeworkApi, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
        body: JSON.stringify({
          enrollment_id: active.enrollmentId,
          lesson_label: active.lesson.lessonNumber,
          score,
          topic: active.lesson.topic,
          lesson_date: active.lesson.date,
          score_type: "Homework",
        }),
      });
      patchHw(active.enrollmentId, active.lesson.lessonNumber, score);
      close();
    } finally {
      setSaving(false);
    }
  }

  function patchAtt(enrollmentId: number, lessonNumber: string, status: AttValue) {
    setData((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        enrollments: prev.enrollments.map((en) => {
          if (en.enrollmentId !== enrollmentId) return en;
          const att = { ...en.attendance };
          if (status) att[lessonNumber] = status;
          else delete att[lessonNumber];
          return { ...en, attendance: att };
        }),
      };
    });
  }

  function patchHw(enrollmentId: number, lessonNumber: string, score: number) {
    setData((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        enrollments: prev.enrollments.map((en) =>
          en.enrollmentId !== enrollmentId
            ? en
            : { ...en, homework: { ...en.homework, [lessonNumber]: score } },
        ),
      };
    });
  }

  async function updateEnrollmentStatus(enrollmentId: number, status: "active" | "disqualified") {
    if (statusSavingId) return;
    let reason = "";
    if (status === "disqualified") {
      reason = window.prompt("Reason for disqualification?", "") || "";
    }
    setStatusSavingId(enrollmentId);
    try {
      const res = await fetch(routes.adminAcademicEnrollmentStatusApi(enrollmentId), {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf,
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({ status, reason }),
      });
      const json = await res.json();
      if (!res.ok || !json.ok) {
        setError(asString(json.message) || "Unable to update enrollment.");
        return;
      }
      await load(groupId);
    } catch {
      setError("Network error.");
    } finally {
      setStatusSavingId(null);
    }
  }

  const lessons = data?.lessons ?? [];
  const enrollments = data?.enrollments ?? [];
  const allEnrollments = data?.allEnrollments ?? enrollments;
  const disqualifiedEnrollments = allEnrollments.filter((en) => en.status === "disqualified");
  const enrollmentQuery = enrollmentSearch.trim().toLowerCase();
  const visibleAllEnrollments = allEnrollments.filter((en) => {
    if (!enrollmentQuery) return true;
    return `${en.fullName} ${en.publicDashboardId || ""}`.toLowerCase().includes(enrollmentQuery);
  });
  const visibleActiveEnrollments = visibleAllEnrollments.filter((en) => en.status !== "disqualified");
  const visibleDisqualifiedEnrollments = visibleAllEnrollments.filter((en) => en.status === "disqualified");

  const popTop = active
    ? Math.min(active.anchorRect.bottom + 4, window.innerHeight - 200)
    : 0;
  const popLeft = active
    ? Math.min(active.anchorRect.left, window.innerWidth - 220)
    : 0;

  return (
    <div className="space-y-3">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-foreground/10 bg-surface px-4 py-3">
        <div className="flex flex-wrap items-center gap-4">
          <button
            type="button"
            onClick={onClose}
            className="inline-flex items-center gap-1 rounded-lg border border-foreground/10 px-2.5 py-1.5 text-xs font-semibold text-muted-foreground hover:bg-muted"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
            Groups
          </button>
          {data && (
            <span className="text-sm font-bold">
              {data.group.name}
              <span className="ml-2 text-xs font-normal text-muted-foreground">
                {data.group.subjectName} · {data.group.schoolCode}
              </span>
            </span>
          )}
          {data && (
            <span className="text-xs text-muted-foreground">
              {enrollments.length} active · {disqualifiedEnrollments.length} disqualified · {lessons.length} lessons
            </span>
          )}
          {/* Legend */}
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <span className="inline-flex h-4 w-4 items-center justify-center rounded bg-emerald-500 text-[9px] font-bold text-white">P</span> Present
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-flex h-4 w-4 items-center justify-center rounded bg-red-500 text-[9px] font-bold text-white">A</span> Absent
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-flex h-4 w-4 items-center justify-center rounded bg-amber-400 text-[9px] font-bold text-white">J</span> Justified
            </span>
          </div>
        </div>
      </div>

      {data && (
        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr),320px]">
          <div className="rounded-xl border border-foreground/8 bg-surface p-4">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm font-bold">Enrollments</p>
                <p className="text-xs text-muted-foreground">
                  Active students stay in gradebook; disqualified students remain visible here.
                </p>
              </div>
              <label className="relative block w-full sm:w-64">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="search"
                  value={enrollmentSearch}
                  onChange={(event) => setEnrollmentSearch(event.target.value)}
                  placeholder="Search enrollments"
                  className="h-9 w-full rounded-lg border border-foreground/10 bg-background pl-9 pr-3 text-sm outline-none focus:border-foreground/30"
                />
              </label>
            </div>
            <div className="grid gap-3 xl:grid-cols-2">
              <EnrollmentList
                title="Active"
                icon={<Users className="h-3.5 w-3.5" />}
                rows={visibleActiveEnrollments}
                emptyText="No active enrollments."
                actionLabel="Disqualify"
                actionIcon={<UserX className="h-3.5 w-3.5" />}
                actionTone="danger"
                savingId={statusSavingId}
                onAction={(enrollmentId) => updateEnrollmentStatus(enrollmentId, "disqualified")}
              />
              <EnrollmentList
                title="Disqualified"
                icon={<UserX className="h-3.5 w-3.5" />}
                rows={visibleDisqualifiedEnrollments}
                emptyText="No disqualified students."
                actionLabel="Restore"
                actionIcon={<RotateCcw className="h-3.5 w-3.5" />}
                actionTone="neutral"
                savingId={statusSavingId}
                onAction={(enrollmentId) => updateEnrollmentStatus(enrollmentId, "active")}
              />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-2 lg:grid-cols-1">
            <MiniMetric icon={<Users className="h-3.5 w-3.5" />} label="Active" value={enrollments.length} />
            <MiniMetric icon={<UserX className="h-3.5 w-3.5" />} label="Disqualified" value={disqualifiedEnrollments.length} />
            <MiniMetric icon={<BookMarked className="h-3.5 w-3.5" />} label="Lessons" value={lessons.length} />
          </div>
        </div>
      )}

      {/* States */}
      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      ) : loading ? (
        <div className="rounded-xl border border-foreground/8 bg-surface p-6 text-center text-sm text-muted-foreground">Loading…</div>
      ) : data && lessons.length === 0 ? (
        <div className="rounded-xl border border-foreground/8 bg-surface p-6 text-center text-sm text-muted-foreground">No lessons found for this group.</div>
      ) : null}

      {/* Gradebook table */}
      {data && lessons.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-foreground/8 bg-surface">
          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse text-left text-xs">
              <thead>
                <tr className="bg-muted/40">
                  <th rowSpan={3} className="sticky left-0 z-20 min-w-[180px] border-b border-r border-foreground/10 bg-muted/40 px-3 py-2 font-bold uppercase tracking-wide text-muted-foreground">
                    Student
                  </th>
                  <th rowSpan={3} className="sticky left-[180px] z-20 min-w-[48px] border-b border-r border-foreground/10 bg-muted/40 px-2 py-2 text-center font-bold uppercase tracking-wide text-muted-foreground">
                    AAP
                  </th>
                  {lessons.map((lesson) => (
                    <th key={lesson.id} colSpan={2} className="border-l border-foreground/10 p-0 text-center">
                      <div
                        title={`${lesson.lessonNumber} - ${lesson.topic}`}
                        className="w-full px-1 py-1"
                      >
                        <span className="block text-[10px] font-semibold leading-tight text-muted-foreground">
                          {lesson.date || lesson.lessonNumber}
                        </span>
                        <span className="block text-[9px] font-normal text-muted-foreground/60">
                          {lesson.lessonNumber}
                        </span>
                      </div>
                    </th>
                  ))}
                </tr>
                {/* Row 2: topic */}
                <tr className="bg-muted/30">
                  {lessons.map((lesson) => (
                    <th key={`${lesson.id}-topic`} colSpan={2} className="border-t border-l border-foreground/10 px-1 py-0.5 text-center">
                      <span className="block truncate max-w-[80px] text-[9px] font-normal italic text-muted-foreground/70">
                        {lesson.topic || "—"}
                      </span>
                    </th>
                  ))}
                </tr>
                {/* Row 3: Att | HW */}
                <tr className="bg-muted/20">
                  {lessons.map((lesson) => (
                    <>
                      <th key={`${lesson.id}-att`} className="w-[28px] border-b border-t border-l border-foreground/10 px-0.5 py-1 text-center font-normal text-muted-foreground/70">Att</th>
                      <th key={`${lesson.id}-hw`} className="w-[36px] border-b border-t border-r border-foreground/10 px-0.5 py-1 text-center font-normal text-muted-foreground/70">HW</th>
                    </>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-foreground/5">
                {enrollments.map((en) => (
                  <tr key={en.enrollmentId} className="hover:bg-foreground/[0.015]">
                    <td className="sticky left-0 z-10 border-r border-foreground/8 bg-surface px-3 py-1 font-semibold text-sm">
                      {en.fullName}
                    </td>
                    <td className="sticky left-[180px] z-10 border-r border-foreground/8 bg-surface px-2 py-1 text-center font-bold text-muted-foreground">
                      {en.averageGrade > 0 ? en.averageGrade.toFixed(0) : "–"}
                    </td>
                    {lessons.map((lesson) => {
                      const att = (en.attendance[lesson.lessonNumber] || "") as AttValue;
                      const hw = en.homework[lesson.lessonNumber];
                      const isActiveAtt = active?.enrollmentId === en.enrollmentId && active?.lesson.id === lesson.id && active?.kind === "att";
                      const isActiveHw = active?.enrollmentId === en.enrollmentId && active?.lesson.id === lesson.id && active?.kind === "hw";
                      return (
                        <>
                          <td key={`${lesson.id}-att`} className="border-l border-foreground/5 p-0 text-center">
                            <button
                              type="button"
                              onClick={(e) => openCell(e, en.enrollmentId, lesson, "att", hw)}
                              title={`${en.fullName} · ${lesson.lessonNumber} · attendance`}
                              className={`h-[26px] w-[28px] rounded text-[10px] font-bold transition-opacity hover:opacity-75 ${att ? attCls(att) : "text-foreground/20"} ${isActiveAtt ? "ring-1 ring-foreground/40" : ""}`}
                            >
                              {att ? attLabel(att) : "·"}
                            </button>
                          </td>
                          <td key={`${lesson.id}-hw`} className="border-r border-foreground/5 p-0 text-center">
                            <button
                              type="button"
                              onClick={(e) => openCell(e, en.enrollmentId, lesson, "hw", hw)}
                              title={`${en.fullName} · ${lesson.lessonNumber} · homework`}
                              className={`h-[26px] w-[36px] rounded text-[10px] transition-opacity hover:opacity-75 ${hw !== undefined ? "font-bold text-blue-600" : "text-foreground/20"} ${isActiveHw ? "ring-1 ring-foreground/40" : ""}`}
                            >
                              {hw !== undefined ? hw : "·"}
                            </button>
                          </td>
                        </>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Popover */}
      {active && (
        <div
          ref={popRef}
          style={{ position: "fixed", top: popTop, left: popLeft, zIndex: 9999 }}
          className="w-52 rounded-xl border border-foreground/10 bg-surface shadow-xl"
        >
          <div className="flex items-center justify-between border-b border-foreground/8 px-3 py-2">
            <div className="min-w-0">
              <p className="truncate text-xs font-bold">{active.lesson.lessonNumber}</p>
              <p className="truncate text-[10px] text-muted-foreground">{active.lesson.topic}</p>
              {active.lesson.date && <p className="text-[10px] text-muted-foreground">{active.lesson.date}</p>}
            </div>
            <button type="button" onClick={close} className="ml-2 shrink-0 rounded p-0.5 hover:bg-muted">
              <X className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
          </div>
          <div className="p-3">
            {active.kind === "att" ? (
              <div className="space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Attendance</p>
                <div className="grid grid-cols-4 gap-1">
                  {(["present", "absent", "justified", ""] as AttValue[]).map((v) => {
                    const lbl = v ? attLabel(v) : "–";
                    const cls = v ? attCls(v) : "bg-muted text-muted-foreground";
                    const currentAtt = data?.enrollments.find((e) => e.enrollmentId === active.enrollmentId)?.attendance[active.lesson.lessonNumber] ?? "";
                    return (
                      <button
                        key={v}
                        type="button"
                        disabled={saving}
                        onClick={() => saveAtt(v as AttValue)}
                        className={`rounded py-1.5 text-xs font-bold transition-opacity disabled:opacity-50 ${cls} ${currentAtt === v ? "ring-2 ring-foreground/30 ring-offset-1" : ""}`}
                      >
                        {lbl}
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Homework Score</p>
                {(() => {
                  const curHw = data?.enrollments.find((e) => e.enrollmentId === active.enrollmentId)?.homework[active.lesson.lessonNumber];
                  return curHw !== undefined ? (
                    <p className="text-[10px] text-muted-foreground">Current: <span className="font-bold text-foreground">{curHw}</span></p>
                  ) : null;
                })()}
                <div className="flex gap-2">
                  <input
                    autoFocus
                    type="number"
                    min="0"
                    max="100"
                    step="0.5"
                    value={hwInput}
                    onChange={(e) => setHwInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && saveHw()}
                    placeholder="0–100"
                    className="w-full rounded-lg border border-foreground/10 bg-background px-2 py-1.5 text-sm outline-none focus:border-foreground/30"
                  />
                  <button
                    type="button"
                    disabled={saving || hwInput === ""}
                    onClick={saveHw}
                    className="shrink-0 rounded-lg bg-primary px-3 py-1.5 text-xs font-bold text-primary-foreground disabled:opacity-50"
                  >
                    Save
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  );
}

// ─── Main panel ───────────────────────────────────────────────────────────────

export default function AcademicPanel({ state, kind }: { state: any; kind: AdminTab }) {
  const props = state.props || {};
  const schools = Array.isArray(props.adminAcademicSchools) ? props.adminAcademicSchools : [];
  const subjects = Array.isArray(props.adminAcademicSubjects) ? props.adminAcademicSubjects : [];
  const groups = Array.isArray(props.adminAcademicGroups) ? props.adminAcademicGroups : [];
  const csrf: string = asString(props.csrfToken);

  const [openGroupId, setOpenGroupId] = useState<number | null>(null);
  const [addGroupOpen, setAddGroupOpen] = useState(false);
  const [groupSearch, setGroupSearch] = useState("");
  const [groupSchool, setGroupSchool] = useState("all");
  const [groupSubject, setGroupSubject] = useState("all");

  const schoolNameByCode = useMemo(() => {
    const result = new Map<string, string>();
    schools.forEach((school: Record<string, unknown>) => {
      const code = asString(school.code);
      if (code) result.set(code, asString(school.name) || code);
    });
    return result;
  }, [schools]);

  const groupSchoolOptions = useMemo(() => {
    const codes = new Set<string>();
    groups.forEach((group: Record<string, unknown>) => {
      const code = asString(group.school_code);
      if (code) codes.add(code);
    });
    return Array.from(codes).sort((a, b) => {
      const left = schoolNameByCode.get(a) || a;
      const right = schoolNameByCode.get(b) || b;
      return left.localeCompare(right);
    });
  }, [groups, schoolNameByCode]);

  const groupSubjectOptions = useMemo(() => {
    const names = new Set<string>();
    groups.forEach((group: Record<string, unknown>) => {
      const name = asString(group.subject_name);
      if (name) names.add(name);
    });
    return Array.from(names).sort((a, b) => a.localeCompare(b));
  }, [groups]);

  const filteredGroups = useMemo(() => {
    const query = groupSearch.trim().toLowerCase();
    return groups.filter((group: Record<string, unknown>) => {
      const name = asString(group.name);
      const subject = asString(group.subject_name);
      const schoolCode = asString(group.school_code);
      const schoolName = schoolNameByCode.get(schoolCode) || schoolCode;
      const matchesQuery =
        !query ||
        `${name} ${subject} ${schoolCode} ${schoolName}`.toLowerCase().includes(query);
      const matchesSchool = groupSchool === "all" || schoolCode === groupSchool;
      const matchesSubject = groupSubject === "all" || subject === groupSubject;
      return matchesQuery && matchesSchool && matchesSubject;
    });
  }, [groups, groupSearch, groupSchool, groupSubject, schoolNameByCode]);

  if (kind === "groups" && openGroupId !== null) {
    return (
      <GroupGradebook
        key={openGroupId}
        groupId={openGroupId}
        csrf={csrf}
        onClose={() => setOpenGroupId(null)}
      />
    );
  }

  return (
    <div className="space-y-4">
      {kind === "subjects" ? (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,380px),1fr]">
          <ChartCard title="Add Subject" icon={<Plus className="h-4 w-4 text-info" />}>
            <form action={routes.adminAcademicSubjectCreate} method="post" className="space-y-3">
              <input type="hidden" name="csrf_token" value={csrf} />
              <label className="block">
                <FieldLabel>School</FieldLabel>
                <Select name="school_code" required>
                  {schools.map((school: Record<string, unknown>) => (
                    <option key={asString(school.code)} value={asString(school.code)}>
                      {asString(school.name)}
                    </option>
                  ))}
                </Select>
              </label>
              <label className="block">
                <FieldLabel>Subject Name</FieldLabel>
                <TextInput name="subject_name" required placeholder="General English" />
              </label>
              <label className="block">
                <FieldLabel>Code</FieldLabel>
                <TextInput name="subject_code" placeholder="ENG" />
              </label>
              <button className="rounded-lg bg-primary px-4 py-2.5 text-sm font-bold text-primary-foreground">Save Subject</button>
            </form>
          </ChartCard>
          <ChartCard title="Subjects" subtitle={`${subjects.length} total`}>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[620px] text-left">
                <thead className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                  <tr><th className="px-3 py-2">School</th><th className="px-3 py-2">Subject</th><th className="px-3 py-2">Code</th><th className="px-3 py-2">Short</th></tr>
                </thead>
                <tbody className="divide-y divide-foreground/5">
                  {subjects.map((subject: Record<string, unknown>) => (
                    <tr key={asNumber(subject.id)}><td className="px-3 py-2 text-xs">{asString(subject.school_name)}</td><td className="px-3 py-2 text-sm font-semibold">{asString(subject.name)}</td><td className="px-3 py-2 text-xs">{asString(subject.code)}</td><td className="px-3 py-2 text-xs">{asString(subject.short_name)}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </ChartCard>
        </div>
      ) : null}

      {kind === "groups" && openGroupId === null ? (
        <>
          {addGroupOpen ? (
            <div
              className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-4"
              onClick={() => setAddGroupOpen(false)}
            >
              <div
                className="w-full max-w-lg overflow-hidden rounded-xl bg-surface shadow-card-hover"
                onClick={(event) => event.stopPropagation()}
              >
                <div className="flex items-center justify-between border-b border-foreground/8 px-4 py-3">
                  <h3 className="text-sm font-bold">Add Group</h3>
                  <button
                    type="button"
                    onClick={() => setAddGroupOpen(false)}
                    className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted"
                    aria-label="Close"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <form action={routes.adminAcademicGroupCreate} method="post" className="space-y-3 px-4 py-4">
                  <input type="hidden" name="csrf_token" value={csrf} />
                  <label className="block">
                    <FieldLabel>School</FieldLabel>
                    <Select name="school_code" required>
                      {schools.map((school: Record<string, unknown>) => (
                        <option key={asString(school.code)} value={asString(school.code)}>
                          {asString(school.name)}
                        </option>
                      ))}
                    </Select>
                  </label>
                  <label className="block">
                    <FieldLabel>Subject</FieldLabel>
                    <Select name="subject_id" required>
                      {subjects.map((subject: Record<string, unknown>) => (
                        <option key={asNumber(subject.id)} value={asNumber(subject.id)}>
                          {asString(subject.school_name)} · {asString(subject.name)}
                        </option>
                      ))}
                    </Select>
                  </label>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <label className="block">
                      <FieldLabel>Group Name</FieldLabel>
                      <TextInput name="group_name" required placeholder="7D" />
                    </label>
                    <label className="block">
                      <FieldLabel>Code</FieldLabel>
                      <TextInput name="group_code" placeholder="7D-Math" />
                    </label>
                  </div>
                  <div className="flex justify-end gap-2 border-t border-foreground/8 pt-3">
                    <button
                      type="button"
                      onClick={() => setAddGroupOpen(false)}
                      className="rounded-lg bg-muted px-4 py-2.5 text-sm font-bold text-muted-foreground hover:bg-foreground/10"
                    >
                      Cancel
                    </button>
                    <button className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-bold text-primary-foreground">
                      <Plus className="h-4 w-4" />
                      Save Group
                    </button>
                  </div>
                </form>
              </div>
            </div>
          ) : null}

            <ChartCard
              title="Groups"
              subtitle={`${filteredGroups.length} shown · ${groups.length} total`}
              icon={<Layers className="h-4 w-4 text-info" />}
              headerActions={
                <button
                  type="button"
                  onClick={() => setAddGroupOpen(true)}
                  className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-xs font-bold text-primary-foreground"
                >
                  <Plus className="h-4 w-4" />
                  Add Group
                </button>
              }
            >
              <div className="mb-3 grid gap-2 lg:grid-cols-[minmax(220px,1fr),180px,220px]">
                <label className="relative block">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <input
                    type="search"
                    value={groupSearch}
                    onChange={(event) => setGroupSearch(event.target.value)}
                    placeholder="Search groups"
                    className="h-10 w-full rounded-lg border border-foreground/10 bg-background pl-9 pr-3 text-sm outline-none focus:border-foreground/30"
                  />
                </label>
                <Select value={groupSchool} onChange={(event) => setGroupSchool(event.target.value)}>
                  <option value="all">All schools</option>
                  {groupSchoolOptions.map((code) => (
                    <option key={code} value={code}>
                      {schoolNameByCode.get(code) || code}
                    </option>
                  ))}
                </Select>
                <Select value={groupSubject} onChange={(event) => setGroupSubject(event.target.value)}>
                  <option value="all">All subjects</option>
                  {groupSubjectOptions.map((subject) => (
                    <option key={subject} value={subject}>
                      {subject}
                    </option>
                  ))}
                </Select>
              </div>

              {filteredGroups.length === 0 ? (
                <div className="rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-8 text-center">
                  <p className="text-sm font-bold">No groups found</p>
                  <p className="mt-1 text-xs text-muted-foreground">Try a different search or filter.</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
                  {filteredGroups.map((group: Record<string, unknown>) => {
                    const id = asNumber(group.id);
                    const name = asString(group.name);
                    const subjectName = asString(group.subject_name);
                    const schoolCode = asString(group.school_code);
                    const schoolName = schoolNameByCode.get(schoolCode) || schoolCode;
                    const studentsCount = asNumber(group.students_count);
                    const disqualifiedCount = asNumber(group.disqualified_count);
                    return (
                      <button
                        key={id}
                        type="button"
                        onClick={() => setOpenGroupId(id)}
                        className="group flex aspect-square min-h-0 flex-col rounded-lg border border-foreground/10 bg-background p-3 text-left transition-colors hover:border-primary/40 hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 sm:p-4"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span
                            className={`h-9 w-9 shrink-0 rounded-lg ${subjectSwatch(subjectName)} sm:h-10 sm:w-10`}
                            aria-hidden="true"
                          />
                          <Pill>{schoolCode || "school"}</Pill>
                        </div>

                        <div className="min-w-0 flex-1 py-3">
                          <span className="block truncate text-lg font-bold leading-tight sm:text-xl">{name}</span>
                          <span className="mt-1 block truncate text-xs text-muted-foreground">
                            {subjectName || "No subject"}
                          </span>
                          <span className="mt-0.5 block truncate text-[11px] text-muted-foreground/80">
                            {schoolName}
                          </span>
                        </div>

                        <div className="flex flex-wrap gap-1.5">
                          <Pill>{studentsCount} active</Pill>
                          {disqualifiedCount > 0 ? <Pill>{disqualifiedCount} disqualified</Pill> : null}
                        </div>

                        <div className="mt-2 flex items-center justify-end border-t border-foreground/8 pt-2">
                          <span className="inline-flex items-center gap-1 text-xs font-bold text-primary">
                            Gradebook
                            <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </ChartCard>
        </>
      ) : null}

    </div>
  );
}
