import { useState, useEffect, useRef } from "react";
import { ClipboardList, X, ChevronDown } from "lucide-react";
import { ChartCard } from "@/components/ChartCard";
import { asNumber, asString } from "../shared";
import { routes } from "@/lib/routes";

// ─── Types ───────────────────────────────────────────────────────────────────

type Lesson = {
  id: number;
  lessonNumber: string;
  topic: string;
  date: string;
  order: number;
};

type Enrollment = {
  enrollmentId: number;
  fullName: string;
  averageGrade: number;
  coins: number;
  attendance: Record<string, string>;   // lesson_number → "present"|"absent"|"justified"
  homework: Record<string, number>;     // lesson_number → score
};

type GradebookData = {
  group: { id: number; name: string; subjectName: string; schoolCode: string };
  lessons: Lesson[];
  enrollments: Enrollment[];
};

// Which cell is being edited: "att" or "hw"
type ActiveCell = {
  enrollmentId: number;
  lesson: Lesson;
  kind: "att" | "hw";
  anchorRect: DOMRect;
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

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

// ─── Component ───────────────────────────────────────────────────────────────

export default function GradebookPanel({ state }: { state: any }) {
  const props = state.props || {};
  const groups: Array<Record<string, unknown>> = Array.isArray(props.adminAcademicGroups)
    ? props.adminAcademicGroups
    : [];

  const [selectedGroupId, setSelectedGroupId] = useState<number>(
    groups.length > 0 ? asNumber(groups[0].id) : 0,
  );
  const [data, setData] = useState<GradebookData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [active, setActive] = useState<ActiveCell | null>(null);
  const [hwInput, setHwInput] = useState("");
  const [saving, setSaving] = useState(false);
  const popRef = useRef<HTMLDivElement>(null);

  const csrf: string = asString(props.csrfToken);

  // ── Load gradebook on group change ────────────────────────────────────────
  useEffect(() => {
    if (selectedGroupId > 0) load(selectedGroupId);
  }, [selectedGroupId]);

  // ── Close popover on outside click ────────────────────────────────────────
  useEffect(() => {
    if (!active) return;
    const handler = (e: MouseEvent) => {
      if (popRef.current && !popRef.current.contains(e.target as Node)) close();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [active]);

  async function load(groupId: number) {
    setLoading(true);
    setError("");
    setActive(null);
    try {
      const res = await fetch(routes.adminAcademicGradebookApi(groupId));
      const json = await res.json();
      if (json.ok) setData(json as GradebookData);
      else setError(json.message || "Failed to load.");
    } catch {
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

  const lessons = data?.lessons ?? [];
  const enrollments = data?.enrollments ?? [];

  // Popover position: keep it on-screen
  const popTop = active
    ? Math.min(active.anchorRect.bottom + 4, window.innerHeight - 200)
    : 0;
  const popLeft = active
    ? Math.min(active.anchorRect.left, window.innerWidth - 220)
    : 0;

  return (
    <div className="space-y-3">
      {/* ── Toolbar ── */}
      <ChartCard
        title="Gradebook"
        subtitle="Attendance (P/A/J) and homework scores per lesson"
        icon={<ClipboardList className="h-4 w-4 text-info" />}
      >
        <div className="flex flex-wrap items-center gap-4">
          {/* Group picker */}
          <label className="flex items-center gap-2 text-sm font-semibold">
            <span className="text-muted-foreground">Group</span>
            <div className="relative">
              <select
                value={selectedGroupId}
                onChange={(e) => setSelectedGroupId(Number(e.target.value))}
                className="appearance-none rounded-lg border border-foreground/10 bg-surface py-1.5 pl-3 pr-7 text-sm font-semibold outline-none focus:border-foreground/30"
              >
                {groups.map((g) => (
                  <option key={asNumber(g.id)} value={asNumber(g.id)}>
                    {asString(g.name)} — {asString(g.subject_name)}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            </div>
          </label>

          {data && (
            <span className="text-xs text-muted-foreground">
              {enrollments.length} students · {lessons.length} lessons
            </span>
          )}

          {/* Legend */}
          <div className="ml-auto flex items-center gap-3 text-xs text-muted-foreground">
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
      </ChartCard>

      {/* ── Errors / loading / empty ── */}
      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      ) : loading ? (
        <div className="rounded-xl border border-foreground/8 bg-surface p-6 text-center text-sm text-muted-foreground">
          Loading…
        </div>
      ) : data && lessons.length === 0 ? (
        <div className="rounded-xl border border-foreground/8 bg-surface p-6 text-center text-sm text-muted-foreground">
          No lessons found for this group.
        </div>
      ) : null}

      {/* ── Main gradebook table ── */}
      {data && lessons.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-foreground/8 bg-surface">
          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse text-left text-xs">
              {/* ── Header row 1: dates ── */}
              <thead>
                <tr className="bg-muted/40">
                  {/* Sticky: Student name */}
                  <th
                    rowSpan={2}
                    className="sticky left-0 z-20 min-w-[180px] border-b border-r border-foreground/10 bg-muted/40 px-3 py-2 font-bold uppercase tracking-wide text-muted-foreground"
                  >
                    Student
                  </th>
                  {/* Sticky: AAP */}
                  <th
                    rowSpan={2}
                    className="sticky left-[180px] z-20 min-w-[48px] border-b border-r border-foreground/10 bg-muted/40 px-2 py-2 text-center font-bold uppercase tracking-wide text-muted-foreground"
                  >
                    AAP
                  </th>
                  {/* One date header spanning 2 columns per lesson */}
                  {lessons.map((lesson) => (
                    <th
                      key={lesson.id}
                      colSpan={2}
                      title={`${lesson.lessonNumber}: ${lesson.topic}`}
                      className="border-b border-l border-foreground/10 px-1 py-1 text-center font-semibold text-muted-foreground"
                    >
                      <span className="block text-[10px] leading-tight">{lesson.date || lesson.lessonNumber}</span>
                      <span className="block truncate max-w-[80px] text-[9px] font-normal opacity-70">{lesson.lessonNumber}</span>
                    </th>
                  ))}
                </tr>
                {/* ── Header row 2: Att | Mark per lesson ── */}
                <tr className="bg-muted/20">
                  {lessons.map((lesson) => (
                    <>
                      <th
                        key={`${lesson.id}-att`}
                        className="w-[28px] border-b border-l border-foreground/10 px-0.5 py-1 text-center font-normal text-muted-foreground/70"
                      >
                        Att
                      </th>
                      <th
                        key={`${lesson.id}-hw`}
                        className="w-[36px] border-b border-r border-foreground/10 px-0.5 py-1 text-center font-normal text-muted-foreground/70"
                      >
                        HW
                      </th>
                    </>
                  ))}
                </tr>
              </thead>

              {/* ── Body ── */}
              <tbody className="divide-y divide-foreground/5">
                {enrollments.map((en) => (
                  <tr key={en.enrollmentId} className="hover:bg-foreground/[0.015]">
                    {/* Student name (sticky) */}
                    <td className="sticky left-0 z-10 border-r border-foreground/8 bg-surface px-3 py-1 font-semibold text-sm">
                      {en.fullName}
                    </td>
                    {/* AAP (sticky) */}
                    <td className="sticky left-[180px] z-10 border-r border-foreground/8 bg-surface px-2 py-1 text-center font-bold text-muted-foreground">
                      {en.averageGrade > 0 ? en.averageGrade.toFixed(0) : "–"}
                    </td>
                    {/* Per-lesson: Attendance cell + Homework cell */}
                    {lessons.map((lesson) => {
                      const att = (en.attendance[lesson.lessonNumber] || "") as AttValue;
                      const hw = en.homework[lesson.lessonNumber];
                      const isActiveAtt =
                        active?.enrollmentId === en.enrollmentId &&
                        active?.lesson.id === lesson.id &&
                        active?.kind === "att";
                      const isActiveHw =
                        active?.enrollmentId === en.enrollmentId &&
                        active?.lesson.id === lesson.id &&
                        active?.kind === "hw";
                      return (
                        <>
                          {/* Attendance cell */}
                          <td
                            key={`${lesson.id}-att`}
                            className="border-l border-foreground/5 p-0 text-center"
                          >
                            <button
                              type="button"
                              onClick={(e) => openCell(e, en.enrollmentId, lesson, "att", hw)}
                              title={`${en.fullName} · ${lesson.lessonNumber} · attendance`}
                              className={`h-[26px] w-[28px] rounded text-[10px] font-bold transition-opacity hover:opacity-75 ${
                                att ? attCls(att) : "text-foreground/20"
                              } ${isActiveAtt ? "ring-1 ring-foreground/40" : ""}`}
                            >
                              {att ? attLabel(att) : "·"}
                            </button>
                          </td>
                          {/* Homework cell */}
                          <td
                            key={`${lesson.id}-hw`}
                            className="border-r border-foreground/5 p-0 text-center"
                          >
                            <button
                              type="button"
                              onClick={(e) => openCell(e, en.enrollmentId, lesson, "hw", hw)}
                              title={`${en.fullName} · ${lesson.lessonNumber} · homework`}
                              className={`h-[26px] w-[36px] rounded text-[10px] transition-opacity hover:opacity-75 ${
                                hw !== undefined
                                  ? "font-bold text-blue-600"
                                  : "text-foreground/20"
                              } ${isActiveHw ? "ring-1 ring-foreground/40" : ""}`}
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

      {/* ── Popover ── */}
      {active && (
        <div
          ref={popRef}
          style={{ position: "fixed", top: popTop, left: popLeft, zIndex: 9999 }}
          className="w-52 rounded-xl border border-foreground/10 bg-surface shadow-xl"
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-foreground/8 px-3 py-2">
            <div className="min-w-0">
              <p className="truncate text-xs font-bold">{active.lesson.lessonNumber}</p>
              <p className="truncate text-[10px] text-muted-foreground">{active.lesson.topic}</p>
              {active.lesson.date && (
                <p className="text-[10px] text-muted-foreground">{active.lesson.date}</p>
              )}
            </div>
            <button type="button" onClick={close} className="ml-2 shrink-0 rounded p-0.5 hover:bg-muted">
              <X className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
          </div>

          <div className="p-3">
            {active.kind === "att" ? (
              /* Attendance picker */
              <div className="space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                  Attendance
                </p>
                <div className="grid grid-cols-4 gap-1">
                  {(["present", "absent", "justified", ""] as AttValue[]).map((v) => {
                    const lbl = v ? attLabel(v) : "–";
                    const cls = v ? attCls(v) : "bg-muted text-muted-foreground";
                    const currentAtt =
                      data?.enrollments.find((e) => e.enrollmentId === active.enrollmentId)
                        ?.attendance[active.lesson.lessonNumber] ?? "";
                    return (
                      <button
                        key={v}
                        type="button"
                        disabled={saving}
                        onClick={() => saveAtt(v as AttValue)}
                        className={`rounded py-1.5 text-xs font-bold transition-opacity disabled:opacity-50 ${cls} ${
                          currentAtt === v ? "ring-2 ring-foreground/30 ring-offset-1" : ""
                        }`}
                      >
                        {lbl}
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : (
              /* Homework score */
              <div className="space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                  Homework Score
                </p>
                {(() => {
                  const curHw = data?.enrollments
                    .find((e) => e.enrollmentId === active.enrollmentId)
                    ?.homework[active.lesson.lessonNumber];
                  return curHw !== undefined ? (
                    <p className="text-[10px] text-muted-foreground">
                      Current: <span className="font-bold text-foreground">{curHw}</span>
                    </p>
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
