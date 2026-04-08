import { GraduationCap } from "lucide-react";
import { ChartCard } from "@/components/ChartCard";
import { ProgressBar } from "@/components/ProgressBar";
import { TelegramLayout, Topbar } from "@/components/TelegramLayout";

interface LessonRow {
  lesson_number: string;
  lesson_topic: string;
  lesson_date_display: string;
  aap_display: string;
  progress_width: number;
  remark: string;
  remark_class: string;
}

interface AapPageProps {
  backUrl?: string;
  studentFullName?: string;
  subjectName?: string;
  lessonRows?: LessonRow[];
}

export default function AAPPage(props: AapPageProps) {
  const lessonRows = Array.isArray(props.lessonRows) ? props.lessonRows : [];

  return (
    <TelegramLayout
      topbar={
        <Topbar
          backUrl={props.backUrl}
          title="Average Academic Performance"
          subtitle={`${props.studentFullName || "Student"} · ${props.subjectName || "Subject"}`}
        />
      }
    >
      <div className="animate-in">
        <ChartCard title="Subject Curriculum" icon={<GraduationCap className="h-4 w-4 text-info" />}>
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
                    <div className="flex items-center gap-2">
                      <strong className="text-xs">{row.aap_display}</strong>
                      <ProgressBar value={row.progress_width} className="h-1.5 flex-1" />
                    </div>
                    <p className="mt-1 text-[10px] font-semibold">{row.remark}</p>
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
                      <th className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Grade</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lessonRows.map((row) => (
                      <tr key={`${row.lesson_number}-${row.lesson_topic}`} className="border-b border-foreground/5">
                        <td className="px-3 py-2.5 text-xs text-muted-foreground">{row.lesson_date_display}</td>
                        <td className="px-3 py-2.5 text-xs font-medium">{row.lesson_number}</td>
                        <td className="px-3 py-2.5 text-xs font-medium">{row.lesson_topic}</td>
                        <td className="px-3 py-2.5">
                          <div className="flex items-center gap-2">
                            <strong className="text-xs">{row.aap_display}</strong>
                            <ProgressBar value={row.progress_width} className="h-1.5 w-20" />
                          </div>
                          <p className="mt-0.5 text-[10px] font-semibold">{row.remark}</p>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">No lesson data available for this subject yet.</p>
          )}
        </ChartCard>
      </div>
    </TelegramLayout>
  );
}
