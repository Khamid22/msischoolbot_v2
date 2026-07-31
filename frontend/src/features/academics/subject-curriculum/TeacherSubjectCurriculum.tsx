import { useEffect, useMemo, useState, type ReactNode } from "react";
import { BookMarked, Clock3, GraduationCap, Layers } from "lucide-react";
import { jsonCsrfHeaders } from "@/shared/lib/api";
import { CurriculumTable } from "./CurriculumTable";
import {
  curriculumApi,
  defaultVariant,
  formatCurriculumUpdatedAt,
  type CurriculumDetail,
  type CurriculumVariantKey,
  type SubjectCurriculumCatalog,
} from "./model";

function metric(label: string, value: number, icon: ReactNode) {
  return (
    <div className="rounded-lg border border-border bg-background px-3 py-2.5">
      <div className="flex items-center gap-2 text-muted-foreground">
        {icon}
        <p className="text-[0.625rem] font-black uppercase tracking-wide">{label}</p>
      </div>
      <p className="mt-1 text-lg font-black">{value}</p>
    </div>
  );
}

export function TeacherSubjectCurriculum({
  initialCatalog,
  csrfToken = "",
}: {
  initialCatalog?: SubjectCurriculumCatalog;
  csrfToken?: string;
}) {
  const [catalog, setCatalog] = useState<SubjectCurriculumCatalog>(
    initialCatalog || { subjects: [] },
  );
  const [subjectId, setSubjectId] = useState<number>(
    initialCatalog?.subjects[0]?.subjectId || 0,
  );
  const initialSubject = initialCatalog?.subjects[0] || null;
  const [variantKey, setVariantKey] = useState<CurriculumVariantKey>(
    defaultVariant(initialSubject),
  );
  const [detail, setDetail] = useState<CurriculumDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (catalog.subjects.length) return;
    setLoading(true);
    void curriculumApi<SubjectCurriculumCatalog>("/api/v1/teacher/subject-curricula")
      .then((nextCatalog) => {
        setCatalog(nextCatalog);
        const first = nextCatalog.subjects[0];
        setSubjectId(first?.subjectId || 0);
        setVariantKey(defaultVariant(first));
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Unable to load subject curricula.");
      })
      .finally(() => setLoading(false));
  }, [catalog.subjects.length]);

  const selectedSubject = useMemo(
    () => catalog.subjects.find((subject) => subject.subjectId === subjectId) || null,
    [catalog.subjects, subjectId],
  );
  const variants = selectedSubject?.variants || [];
  const selectedVariant =
    variants.find((variant) => variant.curriculumKey === variantKey) || variants[0] || null;

  useEffect(() => {
    if (!selectedSubject || !selectedVariant) {
      setDetail(null);
      return;
    }
    setLoading(true);
    setError("");
    const detailUrl = `/api/v1/teacher/subject-curricula/${selectedSubject.subjectId}/${selectedVariant.curriculumKey}`;
    void curriculumApi<CurriculumDetail>(detailUrl)
      .then((nextDetail) => {
        setDetail(nextDetail);
        return curriculumApi(
          `${detailUrl}/viewed`,
          { method: "POST", headers: jsonCsrfHeaders(csrfToken) },
        )
          .then(() => {
            setCatalog((current) => ({
              subjects: current.subjects.map((subject) =>
                subject.subjectId !== selectedSubject.subjectId
                  ? subject
                  : {
                      ...subject,
                      variants: subject.variants.map((variant) =>
                        variant.curriculumKey !== selectedVariant.curriculumKey
                          ? variant
                          : { ...variant, hasUpdates: false },
                      ),
                    },
              ),
            }));
          })
          .catch(() => null);
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Unable to load this curriculum.");
      })
      .finally(() => setLoading(false));
  }, [csrfToken, selectedSubject?.subjectId, selectedVariant?.curriculumKey]);

  function chooseSubject(nextSubjectId: number) {
    const nextSubject = catalog.subjects.find((subject) => subject.subjectId === nextSubjectId);
    setSubjectId(nextSubjectId);
    setVariantKey(defaultVariant(nextSubject));
  }

  if (!loading && !catalog.subjects.length) {
    return (
      <section className="rounded-xl border border-dashed border-border bg-surface px-5 py-14 text-center shadow-card">
        <BookMarked className="mx-auto h-9 w-9 text-muted-foreground/60" />
        <h1 className="mt-4 text-lg font-black">No subject curriculum assigned</h1>
        <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">
          Your active subject assignment has not been configured yet. Contact the Academic Director.
        </p>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <header className="rounded-xl border border-border bg-surface p-4 shadow-card sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-primary">
              <GraduationCap className="h-5 w-5" />
              <p className="text-xs font-black uppercase tracking-wide">Subject Curriculum</p>
            </div>
            <h1 className="mt-1 font-display text-xl font-black sm:text-2xl">
              {selectedSubject?.subjectName || "Your curriculum"}
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Read-only teaching guidance for your assigned subject.
            </p>
          </div>
          {catalog.subjects.length > 1 ? (
            <label className="block w-full lg:w-72">
              <span className="mb-1 block text-[0.6875rem] font-black uppercase tracking-wide text-muted-foreground">
                Subject
              </span>
              <select
                value={subjectId}
                onChange={(event) => chooseSubject(Number(event.target.value))}
                className="h-11 w-full rounded-lg border border-border bg-background px-3 text-sm font-black outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"
              >
                {catalog.subjects.map((subject) => (
                  <option key={subject.subjectId} value={subject.subjectId}>
                    {subject.subjectName}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
        </div>
      </header>

      {variants.length > 1 ? (
        <nav
          className="inline-grid w-full grid-cols-2 rounded-xl border border-border bg-surface p-1 shadow-card sm:w-auto"
          aria-label="Curriculum variants"
        >
          {variants.map((variant) => (
            <button
              key={variant.curriculumKey}
              type="button"
              aria-current={variant.curriculumKey === variantKey ? "page" : undefined}
              onClick={() => setVariantKey(variant.curriculumKey)}
              className={`relative min-h-11 rounded-lg px-5 text-sm font-black ${
                variant.curriculumKey === variantKey
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              {variant.title}
              {variant.hasUpdates ? (
                <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-warning" aria-label="Updated" />
              ) : null}
            </button>
          ))}
        </nav>
      ) : null}

      {selectedVariant ? (
        <section className="rounded-xl border border-border bg-surface p-3 shadow-card sm:p-4">
          <div className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {metric("Rows", selectedVariant.itemCount, <Layers className="h-3.5 w-3.5" />)}
            {metric("Lessons", selectedVariant.lessonCount, <BookMarked className="h-3.5 w-3.5" />)}
            {metric("Exams", selectedVariant.examCount, <GraduationCap className="h-3.5 w-3.5" />)}
            <div className="rounded-lg border border-border bg-background px-3 py-2.5">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Clock3 className="h-3.5 w-3.5" />
                <p className="text-[0.625rem] font-black uppercase tracking-wide">Updated</p>
              </div>
              <p className="mt-1 truncate text-xs font-black">
                {formatCurriculumUpdatedAt(selectedVariant.updatedAt) || "Not available"}
              </p>
            </div>
          </div>
          <CurriculumTable detail={detail} loading={loading} error={error} />
        </section>
      ) : (
        <CurriculumTable detail={null} loading={loading} error={error} />
      )}
    </section>
  );
}
