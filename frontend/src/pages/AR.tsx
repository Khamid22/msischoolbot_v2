import { Calendar } from "lucide-react";
import { ChartCard } from "@/components/ChartCard";
import { TelegramLayout, Topbar } from "@/components/TelegramLayout";

interface LessonRow {
  lesson_number: string;
  lesson_topic: string;
  lesson_date_display: string;
  attendance_status: string;
  attendance_display: string;
}

interface ArPageProps {
  backUrl?: string;
  studentFullName?: string;
  subjectName?: string;
  lessonRows?: LessonRow[];
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

export default function ARPage(props: ArPageProps) {
  const lessonRows = Array.isArray(props.lessonRows) ? props.lessonRows : [];

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
              <div className="space-y-3 sm:hidden">
                {lessonRows.map((row) => (
                  <div key={`${row.lesson_number}-${row.lesson_topic}`} className="rounded-lg border border-foreground/5 p-3">
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <span className="text-[10px] font-medium text-muted-foreground">{row.lesson_date_display}</span>
                      <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-bold">
                        L{row.lesson_number}
                      </span>
                    </div>
                    <p className="mb-2 text-xs font-bold leading-snug">{row.lesson_topic}</p>
                    <span
                      className={`inline-flex min-h-7 items-center rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide ${getStatusClasses(
                        row.attendance_status,
                      )}`}
                    >
                      {row.attendance_display}
                    </span>
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
                    {lessonRows.map((row) => (
                      <tr key={`${row.lesson_number}-${row.lesson_topic}`} className="border-b border-foreground/5">
                        <td className="px-3 py-2.5 text-xs text-muted-foreground">{row.lesson_date_display}</td>
                        <td className="px-3 py-2.5 text-xs font-medium">{row.lesson_number}</td>
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
            <p className="text-sm text-muted-foreground">No lesson attendance data available for this subject yet.</p>
          )}
        </ChartCard>
      </div>
    </TelegramLayout>
  );
}
