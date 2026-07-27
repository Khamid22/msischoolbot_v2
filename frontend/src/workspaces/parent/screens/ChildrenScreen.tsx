import { Activity, BookOpen, ChevronRight, GraduationCap, TrendingUp } from "lucide-react";
import {
  EmptyState,
  formatDate,
  ParentPageHeader,
} from "@/workspaces/parent/components";
import type { ParentChild, ParentLanguage } from "@/workspaces/parent/model";

function ChildDetail({
  child,
  language,
}: {
  child: ParentChild;
  language: ParentLanguage;
}) {
  const isRu = language === "ru";
  return (
    <>
      <ParentPageHeader
        title={child.fullName}
        description={`${child.studentCode} · ${child.schoolName}`}
        action={
          <a
            href={child.dashboardUrl}
            className="inline-flex min-h-11 items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-bold text-primary-foreground shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
          >
            {isRu ? "Полный кабинет" : "To‘liq kabinet"}
          </a>
        }
      />
      <div className="grid gap-3 md:grid-cols-2">
        {child.academicIndicators.map((indicator) => (
          <section key={`${indicator.enrollmentId}-${indicator.subjectName}`} className="rounded-xl border border-border bg-surface p-4 shadow-card">
            <h2 className="font-black text-foreground">
              {indicator.subjectDisplayName || indicator.subjectName}
            </h2>
            <p className="mt-1 text-xs text-muted-foreground">{indicator.groupName}</p>
            <div className="mt-4 grid grid-cols-2 gap-2">
              {[
                [GraduationCap, "AAP", `${indicator.aap || "—"} / 9`],
                [Activity, isRu ? "Посещаемость" : "Davomat", `${indicator.attendanceRate}%`],
                [TrendingUp, isRu ? "Экзамен" : "Imtihon", `${indicator.examPerformance || "—"} / 9`],
                [BookOpen, isRu ? "Программа" : "Dastur", `${indicator.completionRate}%`],
              ].map(([Icon, label, value]) => {
                const MetricIcon = Icon as typeof Activity;
                return (
                  <div key={String(label)} className="rounded-lg bg-muted p-3">
                    <p className="flex items-center gap-1.5 text-[0.6875rem] font-bold text-muted-foreground">
                      <MetricIcon className="h-3.5 w-3.5" />
                      {String(label)}
                    </p>
                    <p className="mt-2 text-base font-black tabular-nums text-foreground">{String(value)}</p>
                  </div>
                );
              })}
            </div>
          </section>
        ))}
      </div>
      <section>
        <h2 className="mb-3 text-base font-black text-foreground">{isRu ? "Последние уроки" : "So‘nggi darslar"}</h2>
        {child.recentLessons.length ? (
          <div className="space-y-2">
            {child.recentLessons.map((lesson, index) => (
              <article key={`${lesson.date}-${lesson.lessonNumber}-${index}`} className="rounded-xl border border-border bg-surface p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-bold text-foreground">{lesson.subjectDisplayName || lesson.subjectName}</h3>
                  <span className="text-xs font-semibold text-muted-foreground">{formatDate(lesson.date)}</span>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">{lesson.topic || lesson.lessonNumber || "—"}</p>
                {lesson.attendanceStatus ? (
                  <p className="mt-2 text-xs font-bold text-foreground">
                    {isRu ? "Посещение:" : "Davomat:"} {lesson.attendanceStatus}
                  </p>
                ) : null}
              </article>
            ))}
          </div>
        ) : (
          <p className="rounded-xl border border-dashed border-border bg-surface p-5 text-sm text-muted-foreground">
            {isRu ? "Записей об уроках пока нет." : "Hozircha dars yozuvlari yo‘q."}
          </p>
        )}
      </section>
    </>
  );
}

export function ChildrenScreen({
  children,
  selectedStudentId,
  language,
}: {
  children: ParentChild[];
  selectedStudentId: number | null;
  language: ParentLanguage;
}) {
  const isRu = language === "ru";
  const selected = children.find((child) => child.studentRowId === selectedStudentId);
  if (selectedStudentId && selected) {
    return <ChildDetail child={selected} language={language} />;
  }

  return (
    <>
      <ParentPageHeader
        title={isRu ? "Дети" : "Bolalar"}
        description={isRu
          ? "Выберите ребёнка, чтобы посмотреть посещаемость, прогресс и уроки."
          : "Davomat, o‘sish va darslarni ko‘rish uchun bolani tanlang."}
      />
      {children.length ? (
        <div className="grid gap-3 md:grid-cols-2">
          {children.map((child) => (
            <a
              key={child.studentRowId}
              href={`/parent/children/${child.studentRowId}`}
              className="group flex min-h-28 items-center gap-3 rounded-xl border border-border bg-surface p-4 shadow-card transition-colors hover:border-primary/35 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
            >
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10 font-black text-primary">
                {child.fullName.slice(0, 2).toUpperCase()}
              </span>
              <div className="min-w-0 flex-1">
                <h2 className="truncate font-black text-foreground">{child.fullName}</h2>
                <p className="mt-1 truncate text-xs text-muted-foreground">{child.studentCode} · {child.schoolName}</p>
                <p className="mt-2 truncate text-xs font-semibold text-muted-foreground">
                  {child.subjects.join(", ") || (isRu ? "Предметы не указаны" : "Fanlar ko‘rsatilmagan")}
                </p>
              </div>
              <ChevronRight className="h-5 w-5 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 motion-reduce:transition-none" />
            </a>
          ))}
        </div>
      ) : (
        <EmptyState
          title={isRu ? "Дети ещё не подключены" : "Bolalar hali ulanmagan"}
          description={isRu
            ? "Попросите школу отправить новую ссылку-приглашение."
            : "Maktabdan yangi taklif havolasini yuborishni so‘rang."}
        />
      )}
    </>
  );
}
