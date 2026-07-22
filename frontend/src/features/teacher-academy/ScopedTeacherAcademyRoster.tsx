import { useEffect, useMemo, useRef, useState } from "react";

import { replaceUrlParams } from "@/features/recruitment/ui";
import {
  TeacherCardGrid,
  TeacherGridEmptyState,
  TeacherRosterToolbar,
  type TeacherAcademyCardModel,
} from "@/features/teacher-academy/TeacherAcademyCards";
import {
  academyRosterPageSize,
  academyStatusPresentation,
  academyTeacherProgress,
  filterAndSortAcademyTeachers,
  type AcademyOptionRow,
  type AcademyTeacher,
  type TeacherAcademySort,
} from "@/features/teacher-academy/model";
import type { ActionMenuItem } from "@/shared/ui/ActionMenu";
import { Pagination } from "@/shared/ui/Pagination";

interface ScopedTeacherAcademyRosterProps {
  teachers: AcademyTeacher[];
  subjects: AcademyOptionRow[];
  onOpenTeacher: (teacher: AcademyTeacher) => void;
  actionsForTeacher: (teacher: AcademyTeacher) => ActionMenuItem[];
}

function initialFilters() {
  if (typeof window === "undefined") {
    return { search: "", subjectId: "", sort: "average_score" as TeacherAcademySort, page: 1 };
  }
  const params = new URLSearchParams(window.location.search);
  const requestedSort = params.get("teacher_sort");
  const requestedPage = Number(params.get("teacher_page") || 1);
  return {
    search: params.get("teacher_search") || "",
    subjectId: params.get("teacher_subject") || "",
    sort: requestedSort === "lessons" || requestedSort === "date"
      ? requestedSort
      : "average_score" as TeacherAcademySort,
    page: Number.isFinite(requestedPage) && requestedPage > 0 ? Math.floor(requestedPage) : 1,
  };
}

function useResponsivePageSize() {
  const [pageSize, setPageSize] = useState(() => (
    academyRosterPageSize(typeof window === "undefined" ? 1280 : window.innerWidth)
  ));
  useEffect(() => {
    let frame = 0;
    const update = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => setPageSize(academyRosterPageSize(window.innerWidth)));
    };
    window.addEventListener("resize", update);
    window.visualViewport?.addEventListener("resize", update);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", update);
      window.visualViewport?.removeEventListener("resize", update);
    };
  }, []);
  return pageSize;
}

function joinedLabel(value: string | undefined) {
  if (!value) return "Not recorded";
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) return value.slice(0, 10);
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "Asia/Tashkent",
  }).format(new Date(parsed));
}

export function ScopedTeacherAcademyRoster({
  teachers,
  subjects,
  onOpenTeacher,
  actionsForTeacher,
}: ScopedTeacherAcademyRosterProps) {
  const initial = useMemo(initialFilters, []);
  const [search, setSearch] = useState(initial.search);
  const [subjectId, setSubjectId] = useState(initial.subjectId);
  const [sort, setSort] = useState<TeacherAcademySort>(initial.sort);
  const [page, setPage] = useState(initial.page);
  const perPage = useResponsivePageSize();
  const previousPageSize = useRef(perPage);

  const filtered = useMemo(
    () => filterAndSortAcademyTeachers(teachers, { search, subjectId, sort }),
    [search, sort, subjectId, teachers],
  );
  const totalPages = Math.max(1, Math.ceil(filtered.length / perPage));
  const visible = filtered.slice((page - 1) * perPage, page * perPage);

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);

  useEffect(() => {
    if (previousPageSize.current === perPage) return;
    previousPageSize.current = perPage;
    setPage(1);
  }, [perPage]);

  useEffect(() => {
    replaceUrlParams({
      teacher_sort: sort !== "average_score" ? sort : null,
      teacher_subject: subjectId || null,
      teacher_search: search || null,
      teacher_page: page > 1 ? String(page) : null,
    });
  }, [page, search, sort, subjectId]);

  const clearFilters = () => {
    setSearch("");
    setSubjectId("");
    setSort("average_score");
    setPage(1);
  };
  const hasFilters = Boolean(search || subjectId || sort !== "average_score");

  const cards: TeacherAcademyCardModel[] = visible.map((teacher) => {
    const progress = academyTeacherProgress(teacher);
    const status = academyStatusPresentation(teacher.academy_status);
    return {
      key: `teacher_academy:${teacher.id}`,
      kind: "teacher_academy",
      fullName: teacher.full_name || "Academy teacher",
      position: teacher.position || "Trainee Teacher",
      subject: teacher.subject || "Subject not set",
      statusLabel: status.label,
      statusTone: status.tone,
      joinedLabel: joinedLabel(teacher.academy_start_date || teacher.created_at),
      passed: progress.passed,
      target: progress.target,
      averageScore: progress.average,
      completed: progress.target > 0
        && progress.passed === progress.target
        && progress.average !== null
        && progress.average > 7,
      primaryLabel: "View journey",
      onOpen: () => onOpenTeacher(teacher),
      actions: actionsForTeacher(teacher),
    };
  });

  const subjectOptions = subjects
    .map((subject) => ({
      id: Number(subject.id || subject.subject_id || subject.subjectId || 0),
      label: String(subject.name || subject.subject_name || subject.subjectName || subject.subject || ""),
    }))
    .filter((subject) => subject.id && subject.label)
    .sort((left, right) => left.label.localeCompare(right.label));
  const firstItem = filtered.length ? ((page - 1) * perPage) + 1 : 0;
  const lastItem = Math.min(filtered.length, page * perPage);

  return (
    <div className="space-y-2">
      <TeacherRosterToolbar
        search={search}
        subjectId={subjectId}
        sort={sort}
        subjects={subjectOptions}
        layout="academy"
        onSearchChange={(value) => {
          setSearch(value);
          setPage(1);
        }}
        onSubjectChange={(value) => {
          setSubjectId(value);
          setPage(1);
        }}
        onSortChange={(value) => {
          setSort(value);
          setPage(1);
        }}
        onClear={clearFilters}
      />

      {cards.length ? <TeacherCardGrid teachers={cards} /> : (
        <TeacherGridEmptyState filtered={hasFilters} onClear={clearFilters} />
      )}

      {filtered.length ? (
        <Pagination
          page={page}
          totalPages={totalPages}
          onPageChange={setPage}
          label={`Showing ${firstItem}–${lastItem} of ${filtered.length}`}
        />
      ) : null}
    </div>
  );
}
