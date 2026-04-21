import { useMemo, useState } from "react";
import { Calendar } from "lucide-react";
import { ChartCard } from "@/components/ChartCard";
import { TelegramLayout, Topbar } from "@/components/TelegramLayout";
import { formatLessonDateDisplay } from "@/lib/lesson-date";

interface LessonRow {
  lesson_number: string;
  lesson_topic: string;
  lesson_date_display: string;
  attendance_type?: string;
  attendance_status: string;
  attendance_display: string;
}

interface ArPageProps {
  backUrl?: string;
  studentFullName?: string;
  subjectName?: string;
  lessonRows?: LessonRow[];
}

function formatLessonNumber(value: string) {
  const normalized = String(value || "")
    .trim()
    .replace(/^lesson\s*/i, "")
    .replace(/^l\s*/i, "")
    .trim();
  return normalized || "—";
}

function getStatusClasses(status: string) {
  const normalized = String(status || "").trim().toLowerCase();
  if (normalized === "present") {
    return "border-success/20 bg-success/10 text-success";
  }
  if (normalized === "absent") {
    return "border-destructive/20 bg-destructive/10 text-destructive";
  }
  if (normalized === "justified") {
    return "border-warning/30 bg-warning/20 text-foreground";
  }
  return "border-foreground/10 bg-muted text-muted-foreground";
}

function normalizeAttendanceType(value: string | undefined) {
  const normalized = String(value || "").trim().toLowerCase();
  if (
    normalized === "lecture" ||
    normalized === "lesson" ||
    normalized.startsWith("lecture") ||
    normalized.startsWith("lesson")
  ) {
    return "Lecture";
  }
  if (normalized === "lab" || normalized.startsWith("lab")) {
    return "Lab";
  }
  return "";
}

export default function ARPage(props: ArPageProps) {
  const lessonRows = Array.isArray(props.lessonRows) ? props.lessonRows : [];
  const isChemistrySubject = String(props.subjectName || "").trim().toLowerCase() === "chemistry";
  const hasTypedRows = lessonRows.some(
    (row) => normalizeAttendanceType(row.attendance_type) !== "",
  );
  const shouldShowTypeSwitcher = isChemistrySubject || hasTypedRows;
  const [selectedType, setSelectedType] = useState<"Lecture" | "Lab">("Lecture");

  const resolveRowType = (row: LessonRow): "Lecture" | "Lab" | "" => {
    const explicitType = normalizeAttendanceType(row.attendance_type);
    if (explicitType) {
      return explicitType as "Lecture" | "Lab";
    }
    // Backward-compatible topic inference for old payloads.
    const topic = String(row.lesson_topic || "").trim().toLowerCase();
    if (topic.endsWith("(lab)")) {
      return "Lab";
    }
    if (topic.endsWith("(lesson)") || topic.endsWith("(lecture)")) {
      return "Lecture";
    }
    return shouldShowTypeSwitcher ? "Lecture" : "";
  };
  const hasLabRows = lessonRows.some((row) => resolveRowType(row) === "Lab");

  const filteredRows = useMemo(() => {
    if (!shouldShowTypeSwitcher) {
      return lessonRows;
    }
    return lessonRows.filter(
      (row) => resolveRowType(row) === selectedType,
    );
  }, [lessonRows, shouldShowTypeSwitcher, selectedType]);

  return (
    <TelegramLayout
      topbar={
        <Topbar
          backUrl={props.backUrl}
          title="Attendance Record"
          subtitle={`${props.studentFullName || "Student"} · ${props.subjectName || "Subject"}`}
        />
      }
    >
      <div className="animate-in">
        <ChartCard title="Attendance By Lesson" icon={<Calendar className="h-4 w-4 text-success" />}>
          {lessonRows.length ? (
            <>
              {shouldShowTypeSwitcher ? (
                <div className="mb-3 flex items-center gap-2">
                  {(["Lecture", "Lab"] as const).map((typeOption) => (
                    <button
                      key={typeOption}
                      type="button"
                      onClick={() => setSelectedType(typeOption)}
                      disabled={typeOption === "Lab" && !hasLabRows}
                      className={`rounded-full px-3 py-1 text-xs font-bold transition-colors ${
                        selectedType === typeOption
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted text-muted-foreground hover:text-foreground"
                      } ${typeOption === "Lab" && !hasLabRows ? "cursor-not-allowed opacity-50" : ""}`}
                      aria-disabled={typeOption === "Lab" && !hasLabRows}
                      title={
                        typeOption === "Lab" && !hasLabRows
                          ? "No lab attendance rows found yet."
                          : undefined
                      }
                    >
                      {typeOption}
                    </button>
                  ))}
                </div>
              ) : null}

              {filteredRows.length ? (
                <>
                  <div className="space-y-3 sm:hidden">
                    {filteredRows.map((row, index) => (
                      <div
                        key={`${row.lesson_number}-${row.lesson_topic}-${row.lesson_date_display}-${index}`}
                        className="rounded-lg border border-foreground/5 p-3"
                      >
                        <div className="mb-2 flex items-center justify-between gap-2">
                          <span className="text-[10px] font-medium text-muted-foreground">
                            {formatLessonDateDisplay(row.lesson_date_display)}
                          </span>
                          <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-bold">
                            Lesson {formatLessonNumber(row.lesson_number)}
                          </span>
                        </div>
                        <div className="flex items-start justify-between gap-3">
                          <p className="flex-1 text-xs font-bold leading-snug">{row.lesson_topic}</p>
                          <span
                            className={`inline-flex min-h-7 shrink-0 items-center rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide ${getStatusClasses(
                              row.attendance_status,
                            )}`}
                          >
                            {row.attendance_display}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="hidden overflow-x-auto sm:block">
                    <table className="w-full min-w-[560px] text-left">
                      <thead>
                        <tr className="border-b border-foreground/5">
                          <th className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Date</th>
                          <th className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Lesson</th>
                          <th className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Topic</th>
                          <th className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredRows.map((row, index) => (
                          <tr
                            key={`${row.lesson_number}-${row.lesson_topic}-${row.lesson_date_display}-${index}`}
                            className="border-b border-foreground/5"
                          >
                            <td className="px-3 py-2.5 text-xs text-muted-foreground">
                              {formatLessonDateDisplay(row.lesson_date_display)}
                            </td>
                            <td className="px-3 py-2.5 text-xs font-medium">{formatLessonNumber(row.lesson_number)}</td>
                            <td className="px-3 py-2.5 text-xs font-medium">{row.lesson_topic}</td>
                            <td className="px-3 py-2.5">
                              <span
                                className={`inline-flex min-h-7 items-center rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide ${getStatusClasses(
                                  row.attendance_status,
                                )}`}
                              >
                                {row.attendance_display}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No {selectedType.toLowerCase()} attendance data available yet.
                </p>
              )}
            </>
          ) : (
            <p className="text-sm text-muted-foreground">No lesson attendance data available for this subject yet.</p>
          )}
        </ChartCard>
      </div>
    </TelegramLayout>
  );
}
