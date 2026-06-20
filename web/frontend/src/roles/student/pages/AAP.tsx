import { GraduationCap } from "lucide-react";
import { AdminEmbedLayout, isAdminEmbedMode } from "@/shared/ui/AdminEmbedLayout";
import { ChartCard } from "@/shared/ui/ChartCard";
import { ProgressBar } from "@/shared/ui/ProgressBar";
import { TelegramLayout, Topbar } from "@/shared/ui/TelegramLayout";
import { formatLessonDateDisplay } from "@/shared/lib/lesson-date";

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
  embedMode?: string;
}

export default function AAPPage(props: AapPageProps) {
  const lessonRows = Array.isArray(props.lessonRows) ? props.lessonRows : [];
  const isChemistrySubject =
    String(props.subjectName || "").trim().toLowerCase() === "chemistry";
  const isAdminEmbed = isAdminEmbedMode(props.embedMode);

  const firstColumnLabel = isChemistrySubject ? "Task" : "Date";
  const subtitle = `${props.studentFullName || "Student"} · ${props.subjectName || "Subject"}`;
  const curriculumContent = lessonRows.length ? (
    <>
      <div className="space-y-3 sm:hidden">
        {lessonRows.map((row, index) => (
          <div
            key={`${row.lesson_number}-${row.lesson_topic}-${row.lesson_date_display}-${index}`}
            className="rounded-lg border border-foreground/5 p-3"
          >
            <div className="mb-2 flex items-center justify-between gap-2">
              <p className="text-[10px] font-medium text-muted-foreground">
                {formatLessonDateDisplay(row.lesson_date_display)}
              </p>

              <p className="text-[10px] font-bold text-muted-foreground">
                Lesson {row.lesson_number || "-"}
              </p>
            </div>

            <p className="mb-2 text-xs font-bold leading-snug">
              {row.lesson_topic || "-"}
            </p>

            <div className="flex items-center gap-2">
              <strong className="text-xs">{row.aap_display || "-"}</strong>
              <ProgressBar
                value={row.progress_width || 0}
                className="h-1.5 flex-1"
              />
            </div>

            <p className="mt-1 text-[10px] font-semibold">
              {row.remark || "-"}
            </p>
          </div>
        ))}
      </div>
      <div className="hidden max-h-[70dvh] overflow-auto sm:block">
        <table className="w-full min-w-[760px] text-left">
          <thead className="sticky top-0 z-20 bg-surface shadow-[0_1px_0_hsl(var(--foreground)/0.08)]">
            <tr className="border-b border-foreground/5">
              <th className="w-[16%] px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                {firstColumnLabel}
              </th>

              <th className="w-[14%] px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                Lesson Number
              </th>

              <th className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                Lesson Topic
              </th>

              <th className="w-[26%] px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                Homework Progress
              </th>
            </tr>
          </thead>

          <tbody>
            {lessonRows.map((row, index) => (
              <tr
                key={`${row.lesson_number}-${row.lesson_topic}-${row.lesson_date_display}-${index}`}
                className="border-b border-foreground/5 last:border-b-0"
              >
                <td className="px-3 py-3 text-xs text-muted-foreground">
                  {formatLessonDateDisplay(row.lesson_date_display)}
                </td>

                <td className="px-3 py-3 text-xs font-medium">
                  {row.lesson_number || "-"}
                </td>

                <td className="px-3 py-3 text-xs font-medium">
                  {row.lesson_topic || "-"}
                </td>

                <td className="px-3 py-3">
                  <div className="flex items-center gap-2">
                    <strong className="w-8 shrink-0 text-xs">
                      {row.aap_display || "-"}
                    </strong>

                    <ProgressBar
                      value={row.progress_width || 0}
                      className="h-2 min-w-[6rem] flex-1"
                    />
                  </div>

                  <p className="mt-0.5 text-[10px] font-semibold">
                    {row.remark || "-"}
                  </p>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  ) : (
    <p className="text-sm text-muted-foreground">
      No lesson data available for this subject yet.
    </p>
  );

  if (isAdminEmbed) {
    return (
      <AdminEmbedLayout
        title="Average Academic Performance"
        subtitle={subtitle}
        backUrl={props.backUrl}
        badge="AAP"
      >
        <ChartCard
          title="Subject Curriculum"
          icon={<GraduationCap className="h-4 w-4 text-info" />}
        >
          {curriculumContent}
        </ChartCard>
      </AdminEmbedLayout>
    );
  }

  return (
    <TelegramLayout
      topbar={
        <Topbar
          backUrl={props.backUrl}
          title="Average Academic Performance"
          subtitle={subtitle}
        />
      }
    >
      <div className="animate-in">
        <ChartCard
          title="Subject Curriculum"
          icon={<GraduationCap className="h-4 w-4 text-info" />}
        >
          {curriculumContent}
        </ChartCard>
      </div>
    </TelegramLayout>
  );
}
