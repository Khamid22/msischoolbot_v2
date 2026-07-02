import { useState, useMemo } from "react";
import { ArrowRight, BookMarked, Filter, Layers, Plus, Search, Trash2, Users, X } from "lucide-react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { routes } from "@/shared/lib/routes";
import { csrfHeaders } from "@/shared/lib/api";
import { asNumber, asString, AdminTab, normalizeSubjectKey } from "../shared";
import { FieldLabel, TextInput, Select, Pill, MiniMetric, CompactMetric, subjectSwatches, compareSubjectsByPreferredOrder, programInitials, Lesson } from "./academic/shared";
import { GroupGradebook } from "./academic/GroupGradebook";
import { SchedulePanel } from "./academic/SchedulePanel";

export default function AcademicPanel({ state, kind }: { state: any; kind: AdminTab }) {
  const props = state.props || {};
  const isTeacherMode = asString(state.adminMode).toLowerCase() === "teacher";
  const schools = Array.isArray(props.adminAcademicSchools) ? props.adminAcademicSchools : [];
  const subjects = Array.isArray(props.adminAcademicSubjects) ? props.adminAcademicSubjects : [];
  const initialGroups = Array.isArray(props.adminAcademicGroups) ? props.adminAcademicGroups : [];
  const curriculumPrograms = Array.isArray(props.adminAcademicCurriculumPrograms)
    ? props.adminAcademicCurriculumPrograms
    : [];
  const curriculumItems = Array.isArray(props.adminAcademicCurriculumItems)
    ? props.adminAcademicCurriculumItems
    : [];
  const csrf: string = asString(props.csrfToken);

  const [openGroupId, setOpenGroupId] = useState<number | null>(null);
  const [openProgramId, setOpenProgramId] = useState<number | null>(null);
  const [programSearch, setProgramSearch] = useState("");
  const [programTypeFilter, setProgramTypeFilter] = useState<"all" | "lesson" | "exam">("all");
  const [addGroupOpen, setAddGroupOpen] = useState(false);
  const [manageSchoolsOpen, setManageSchoolsOpen] = useState(false);
  const [groupSearch, setGroupSearch] = useState("");
  const [groupSchool, setGroupSchool] = useState<string>("all");
  const [groupSubject, setGroupSubject] = useState("all");
  const [groupFiltersOpen, setGroupFiltersOpen] = useState(false);
  const [groupRowsOverride, setGroupRowsOverride] = useState<Array<Record<string, unknown>> | null>(null);
  const [deletingGroupId, setDeletingGroupId] = useState<number | null>(null);
  const [groupDeleteError, setGroupDeleteError] = useState("");
  const groups = groupRowsOverride ?? initialGroups;

  const schoolNameByCode = useMemo(() => {
    const result = new Map<string, string>();
    schools.forEach((school: Record<string, unknown>) => {
      const code = asString(school.code);
      if (code) result.set(code, asString(school.name) || code);
    });
    return result;
  }, [schools]);

  const schoolStats = useMemo(() => {
    const map = new Map<string, { groups: number; activeStudents: number; programs: Set<string> }>();
    groups.forEach((group: Record<string, unknown>) => {
      const code = asString(group.school_code);
      if (!code) return;
      const entry = map.get(code) ?? { groups: 0, activeStudents: 0, programs: new Set<string>() };
      entry.groups += 1;
      entry.activeStudents += asNumber(group.students_count);
      const subject = asString(group.subject_name);
      if (subject) entry.programs.add(normalizeSubjectKey(subject));
      map.set(code, entry);
    });
    return map;
  }, [groups]);

  const subjectFilterOptions = useMemo(() => {
    const map = new Map<string, { name: string; groups: number; students: number }>();
    groups.forEach((group: Record<string, unknown>) => {
      if (groupSchool !== "all" && asString(group.school_code) !== groupSchool) return;
      const name = asString(group.subject_name);
      if (!name) return;
      const key = normalizeSubjectKey(name);
      const entry = map.get(key) ?? { name, groups: 0, students: 0 };
      entry.groups += 1;
      entry.students += asNumber(group.students_count);
      map.set(key, entry);
    });
    return Array.from(map.values()).sort((a, b) => compareSubjectsByPreferredOrder(a.name, b.name));
  }, [groups, groupSchool]);

  // Assign each distinct program a stable palette color (index-based, not hashed)
  // so different programs are always visually distinct — the old hash collided.
  const programColor = useMemo(() => {
    const programNames = groups
      .map((group: Record<string, unknown>) => asString(group.subject_name))
      .filter((name: string) => Boolean(name));
    const names = Array.from(new Set<string>(programNames)).sort((left: string, right: string) =>
      left.localeCompare(right),
    );
    const map = new Map<string, string>();
    names.forEach((name, index) => map.set(name, subjectSwatches[index % subjectSwatches.length]));
    return (name: unknown) => map.get(asString(name)) ?? subjectSwatches[0];
  }, [groups]);

  const selectedSchool =
    groupSchool === "all"
      ? null
      : schools.find((school: Record<string, unknown>) => asString(school.code) === groupSchool) || null;

  const contextSummary = useMemo(() => {
    if (groupSchool === "all") {
      const programs = new Set<string>();
      let activeStudents = 0;
      groups.forEach((group: Record<string, unknown>) => {
        activeStudents += asNumber(group.students_count);
        const subject = asString(group.subject_name);
        if (subject) programs.add(normalizeSubjectKey(subject));
      });
      return { groups: groups.length, activeStudents, programs: programs.size };
    }
    const stats = schoolStats.get(groupSchool);
    return {
      groups: stats?.groups ?? 0,
      activeStudents: stats?.activeStudents ?? 0,
      programs: stats?.programs.size ?? 0,
    };
  }, [groupSchool, groups, schoolStats]);

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
  const filteredGroupSections = useMemo(() => {
    const sections = new Map<string, { name: string; groups: Record<string, unknown>[] }>();
    filteredGroups.forEach((group: Record<string, unknown>) => {
      const name = asString(group.subject_name) || "No program";
      const key = normalizeSubjectKey(name);
      const section = sections.get(key) ?? { name, groups: [] };
      section.groups.push(group);
      sections.set(key, section);
    });
    return Array.from(sections.values()).sort((left, right) => compareSubjectsByPreferredOrder(left.name, right.name));
  }, [filteredGroups]);
  const activeGroupFilterCount =
    (groupSchool !== "all" ? 1 : 0) +
    (groupSubject !== "all" ? 1 : 0) +
    (groupSearch.trim() ? 1 : 0);

  async function deleteGroup(group: Record<string, unknown>) {
    if (isTeacherMode || deletingGroupId !== null) return;
    const id = asNumber(group.id);
    const name = asString(group.name) || "this group";
    if (!id) return;

    const studentsCount = asNumber(group.students_count);
    const disqualifiedCount = asNumber(group.disqualified_count);
    const enrollmentSummary = studentsCount + disqualifiedCount > 0
      ? ` This will remove ${studentsCount} active and ${disqualifiedCount} disqualified enrollment(s) from the group.`
      : "";
    const confirmed = window.confirm(
      `Delete ${name}? This removes the group, schedule, lessons, attendance, homework, exam records, and group enrollments. Student accounts stay in the system.${enrollmentSummary}`,
    );
    if (!confirmed) return;

    setDeletingGroupId(id);
    setGroupDeleteError("");
    try {
      const response = await fetch(routes.adminAcademicGroupApi(id), {
        method: "DELETE",
        headers: csrfHeaders(csrf),
      });
      const json = await response.json();
      if (!response.ok || !json.ok) {
        setGroupDeleteError(asString(json.message) || "Unable to delete group.");
        return;
      }
      if (Array.isArray(json.groups)) {
        setGroupRowsOverride(json.groups);
      } else {
        setGroupRowsOverride((current) =>
          (current ?? groups).filter((row: Record<string, unknown>) => asNumber(row.id) !== id),
        );
      }
      if (openGroupId === id) setOpenGroupId(null);
    } catch {
      setGroupDeleteError("Network error while deleting the group.");
    } finally {
      setDeletingGroupId(null);
    }
  }

  const activeProgram =
    curriculumPrograms.find((program: Record<string, unknown>) => asNumber(program.id) === openProgramId) ||
    curriculumPrograms[0] ||
    null;
  const activeProgramId = asNumber(activeProgram?.id);
  const activeProgramItems = useMemo(() => {
    const query = programSearch.trim().toLowerCase();
    return curriculumItems
      .filter((item: Record<string, unknown>) => asNumber(item.program_id) === activeProgramId)
      .filter((item: Record<string, unknown>) => {
        if (programTypeFilter !== "all" && asString(item.item_type) !== programTypeFilter) return false;
        if (!query) return true;
        return [
          item.lesson_number,
          item.title,
          item.item_type,
          item.term_label,
          item.week_label,
          item.specification_points,
          item.book_pages,
        ]
          .map(asString)
          .join(" ")
          .toLowerCase()
          .includes(query);
      });
  }, [activeProgramId, curriculumItems, programSearch, programTypeFilter]);

  if (kind === "groups" && openGroupId !== null) {
    return (
      <GroupGradebook
        key={openGroupId}
        groupId={openGroupId}
        csrf={csrf}
        groups={groups}
        onClose={() => setOpenGroupId(null)}
      />
    );
  }

  if (kind === "schedule") {
    return <SchedulePanel state={state} />;
  }

  return (
    <div className={kind === "groups" ? "flex flex-col gap-4 lg:h-full lg:min-h-0" : "space-y-4"}>
      {kind === "subjects" ? (
        <div className="space-y-3">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <label className="flex min-w-0 items-center gap-2">
              <BookMarked className="h-4 w-4 shrink-0 text-info" />
              <select
                value={activeProgramId || ""}
                onChange={(event) => {
                  setOpenProgramId(Number(event.target.value));
                  setProgramSearch("");
                }}
                className="h-9 min-w-0 max-w-full rounded-lg border border-foreground/10 bg-surface px-3 text-sm font-bold outline-none focus:border-foreground/30"
                aria-label="Subject program"
              >
                {curriculumPrograms.length ? (
                  curriculumPrograms.map((program: Record<string, unknown>) => {
                    const programId = asNumber(program.id);
                    return (
                      <option key={programId} value={programId}>
                        {asString(program.subject_name)} · {asNumber(program.lesson_count)} lessons · {asNumber(program.exam_count)} exams
                      </option>
                    );
                  })
                ) : (
                  <option value="">No scheme of work programs yet</option>
                )}
              </select>
            </label>
          </div>

          <ChartCard
              title={activeProgram ? asString(activeProgram.subject_name) : "Program"}
              subtitle={
                activeProgram
                  ? asString(activeProgram.source_file)
                  : "Select a subject program"
              }
              headerActions={
                <div className="relative w-full max-w-sm">
                  <Search className="pointer-events-none absolute left-3 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                  <input
                    type="search"
                    value={programSearch}
                    onChange={(event) => setProgramSearch(event.target.value)}
                    placeholder="Search program"
                    className="h-9 w-full rounded-lg border border-foreground/10 bg-surface pl-8 pr-3 text-xs font-semibold outline-none focus:border-foreground/30"
                  />
                </div>
              }
            >
              <div className="mb-3 grid gap-2 sm:grid-cols-3">
                <MiniMetric icon={<BookMarked className="h-3.5 w-3.5" />} label="Program Rows" value={asNumber(activeProgram?.total_items)} />
                <MiniMetric icon={<Layers className="h-3.5 w-3.5" />} label="Lessons" value={asNumber(activeProgram?.lesson_count)} />
                <MiniMetric icon={<BookMarked className="h-3.5 w-3.5" />} label="Exams" value={asNumber(activeProgram?.exam_count)} />
              </div>

              <div className="mb-3 flex flex-wrap items-center gap-2">
                {[
                  { key: "all", label: "All" },
                  { key: "lesson", label: "Lessons" },
                  { key: "exam", label: "Exams" },
                ].map((option) => {
                  const active = programTypeFilter === option.key;
                  return (
                    <button
                      key={option.key}
                      type="button"
                      onClick={() => setProgramTypeFilter(option.key as "all" | "lesson" | "exam")}
                      className={`h-8 rounded-lg px-3 text-xs font-bold transition-colors ${
                        active
                          ? "bg-foreground text-background"
                          : "border border-foreground/10 bg-surface text-muted-foreground hover:bg-muted hover:text-foreground"
                      }`}
                    >
                      {option.label}
                    </button>
                  );
                })}
                <span className="ml-auto text-xs font-semibold text-muted-foreground">
                  {activeProgramItems.length} shown
                </span>
              </div>

              <div className="miniapp-table-scroll max-h-[62dvh] rounded-lg border border-foreground/8">
                {activeProgramItems.length ? (
                  <div className="divide-y divide-foreground/6">
                    {activeProgramItems.map((item: Record<string, unknown>) => {
                      const itemType = asString(item.item_type);
                      const isExam = itemType === "exam";
                      return (
                        <div
                          key={asNumber(item.id)}
                          className={`grid gap-3 px-3 py-3 md:grid-cols-[5.25rem_1fr_9rem_8rem] ${
                            isExam ? "bg-amber-50/70" : "bg-surface"
                          }`}
                        >
                          <div>
                            <p className="text-xs font-bold text-foreground">{asString(item.lesson_number)}</p>
                            <span
                              className={`mt-1 inline-flex rounded-md px-2 py-0.5 text-[10px] font-bold ${
                                isExam
                                  ? "bg-amber-100 text-amber-800"
                                  : "bg-muted text-muted-foreground"
                              }`}
                            >
                              {isExam ? "Exam" : "Lesson"}
                            </span>
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-bold leading-5">{asString(item.title)}</p>
                            {asString(item.specification_points) ? (
                              <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">
                                {asString(item.specification_points)}
                              </p>
                            ) : null}
                          </div>
                          <div className="text-xs leading-5 text-muted-foreground">
                            <span className="font-semibold text-foreground">{asString(item.term_label) || "Term not set"}</span>
                            <br />
                            {asString(item.week_label) || "Week not set"}
                          </div>
                          <div className="text-xs leading-5 text-muted-foreground">
                            {asString(item.book_pages) || "No book pages"}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="px-4 py-12 text-center text-sm font-bold text-muted-foreground">
                    No program items match this search.
                  </p>
                )}
              </div>
            </ChartCard>

        </div>
      ) : null}

      {kind === "groups" && openGroupId === null ? (
        <>
          {addGroupOpen && !isTeacherMode ? (
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
                  {selectedSchool ? (
                    <>
                      <input type="hidden" name="school_code" value={asString(selectedSchool.code)} />
                      <div className="rounded-lg border border-foreground/10 bg-muted/40 px-3 py-2.5">
                        <FieldLabel>Client School</FieldLabel>
                        <div className="flex items-center gap-2">
                          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary">
                            <Users className="h-3.5 w-3.5" />
                          </span>
                          <p className="text-sm font-bold">{asString(selectedSchool.name)}</p>
                        </div>
                      </div>
                    </>
                  ) : (
                    <label className="block">
                      <FieldLabel>Client School</FieldLabel>
                      <Select name="school_code" required defaultValue="">
                        <option value="" disabled>
                          Choose a client school
                        </option>
                        {schools.map((school: Record<string, unknown>) => (
                          <option key={asString(school.code)} value={asString(school.code)}>
                            {asString(school.name)}
                          </option>
                        ))}
                      </Select>
                    </label>
                  )}
                  <label className="block">
                    <FieldLabel>Subject Program</FieldLabel>
                    <Select name="program_subject_key" required>
                      {curriculumPrograms.length === 0 ? (
                        <option value="" disabled>No programs imported yet</option>
                      ) : (
                        curriculumPrograms.map((program: Record<string, unknown>) => (
                          <option key={asString(program.subject_key)} value={asString(program.subject_key)}>
                            {asString(program.subject_name)}
                          </option>
                        ))
                      )}
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

            {manageSchoolsOpen && !isTeacherMode ? (
              <div
                className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-4"
                onClick={() => setManageSchoolsOpen(false)}
              >
                <div
                  className="flex max-h-[85dvh] w-full max-w-lg flex-col overflow-hidden rounded-xl bg-surface shadow-card-hover"
                  onClick={(event) => event.stopPropagation()}
                >
                  <div className="flex items-center justify-between border-b border-foreground/8 px-4 py-3">
                    <div>
                      <h3 className="text-sm font-bold">Client Schools</h3>
                      <p className="text-xs text-muted-foreground">{schools.length} registered</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setManageSchoolsOpen(false)}
                      className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted"
                      aria-label="Close"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4">
                    <form action={routes.adminAcademicSchoolCreate} method="post" className="space-y-3 rounded-xl border border-foreground/8 bg-background p-4">
                      <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Add a client school</p>
                      <input type="hidden" name="csrf_token" value={csrf} />
                      <div className="grid gap-3 sm:grid-cols-2">
                        <label className="block">
                          <FieldLabel>School Name</FieldLabel>
                          <TextInput name="school_name" required placeholder="e.g. School 5" />
                        </label>
                        <label className="block">
                          <FieldLabel>Code (optional)</FieldLabel>
                          <TextInput name="school_code" placeholder="e.g. school5" />
                        </label>
                      </div>
                      <div className="flex justify-end">
                        <button className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-bold text-primary-foreground">
                          <Plus className="h-4 w-4" />
                          Save School
                        </button>
                      </div>
                    </form>
                    {schools.length === 0 ? (
                      <div className="rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-6 text-center">
                        <p className="text-sm font-bold text-muted-foreground">No client schools registered yet.</p>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {schools.map((school: Record<string, unknown>) => {
                          const code = asString(school.code);
                          const stats = schoolStats.get(code);
                          return (
                            <div
                              key={code}
                              className="flex items-center justify-between gap-3 rounded-lg border border-foreground/8 bg-background px-3 py-2.5"
                            >
                              <div className="flex min-w-0 items-center gap-2.5">
                                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                                  <Users className="h-4 w-4" />
                                </span>
                                <div className="min-w-0">
                                  <p className="truncate text-sm font-bold">{asString(school.name)}</p>
                                  <p className="truncate text-[11px] text-muted-foreground">{code}</p>
                                </div>
                              </div>
                              <div className="flex shrink-0 gap-1.5">
                                <Pill>{stats?.groups ?? 0} groups</Pill>
                                <Pill>{stats?.activeStudents ?? 0} students</Pill>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : null}

            <section className="relative flex min-h-0 flex-col rounded-lg border border-foreground/10 bg-surface p-2.5 shadow-card lg:flex-1">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
                    <div className="flex min-w-0 items-center gap-2">
                      <Users className="h-4 w-4 text-info" />
                      <h3 className="truncate text-sm font-bold">Client Schools & Groups</h3>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      <CompactMetric icon={<Layers className="h-3 w-3" />} label="groups" value={contextSummary.groups} />
                      <CompactMetric icon={<Users className="h-3 w-3" />} label="students" value={contextSummary.activeStudents} />
                      <CompactMetric icon={<BookMarked className="h-3 w-3" />} label="programs" value={contextSummary.programs} />
                    </div>
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {selectedSchool ? asString(selectedSchool.name) : "All schools"} · {filteredGroups.length} shown
                  </p>
                </div>
                <div className="flex shrink-0 flex-wrap gap-1.5">
                  <button
                    type="button"
                    onClick={() => setGroupFiltersOpen((open) => !open)}
                    className={`inline-flex h-8 items-center gap-1.5 rounded-md border px-2.5 text-xs font-bold transition-colors ${
                      groupFiltersOpen || activeGroupFilterCount > 0
                        ? "border-primary/50 bg-primary/10 text-primary"
                        : "border-foreground/10 bg-background text-foreground hover:bg-muted"
                    }`}
                    aria-expanded={groupFiltersOpen}
                  >
                    <Filter className="h-3.5 w-3.5" />
                    Filters
                    {activeGroupFilterCount > 0 ? (
                      <span className="rounded bg-primary/15 px-1.5 py-0.5 text-[10px] text-primary">
                        {activeGroupFilterCount}
                      </span>
                    ) : null}
                  </button>
                  {!isTeacherMode ? (
                    <>
                      <button
                        type="button"
                        onClick={() => setManageSchoolsOpen(true)}
                        className="inline-flex h-8 items-center gap-1.5 rounded-md border border-foreground/10 bg-background px-2.5 text-xs font-bold text-foreground hover:bg-muted"
                      >
                        <Users className="h-3.5 w-3.5" />
                        Schools
                      </button>
                      <button
                        type="button"
                        disabled={schools.length === 0}
                        onClick={() => setAddGroupOpen(true)}
                        className="inline-flex h-8 items-center gap-1.5 rounded-md bg-primary px-2.5 text-xs font-bold text-primary-foreground disabled:opacity-50"
                      >
                        <Plus className="h-3.5 w-3.5" />
                        Add Group
                      </button>
                    </>
                  ) : null}
                </div>
              </div>

              {groupFiltersOpen ? (
                <div className="absolute right-2 top-12 z-30 w-[min(42rem,calc(100vw-2rem))] rounded-lg border border-foreground/10 bg-surface p-3 shadow-card-hover">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Filters</p>
                    <button
                      type="button"
                      onClick={() => {
                        setGroupSearch("");
                        setGroupSchool("all");
                        setGroupSubject("all");
                      }}
                      className="text-xs font-bold text-primary hover:text-primary/80"
                    >
                      Reset
                    </button>
                  </div>
                  <label className="relative mt-2 block">
                    <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                    <input
                      type="search"
                      value={groupSearch}
                      onChange={(event) => setGroupSearch(event.target.value)}
                      placeholder="Search group, school, or subject"
                      className="h-9 w-full rounded-md border border-foreground/10 bg-background pl-8 pr-2.5 text-xs font-semibold outline-none focus:border-foreground/30"
                    />
                  </label>
                  <div className="mt-3 space-y-2">
                    <div>
                      <p className="mb-1.5 text-[10px] font-bold uppercase tracking-wide text-muted-foreground">School</p>
                      <div className="flex flex-wrap gap-1.5">
                        <button
                          type="button"
                          onClick={() => {
                            setGroupSchool("all");
                            setGroupSubject("all");
                          }}
                          className={`inline-flex h-7 items-center gap-1.5 rounded-md border px-2 text-[11px] font-bold transition-colors ${
                            groupSchool === "all"
                              ? "border-primary/50 bg-primary/10 text-primary"
                              : "border-foreground/10 bg-background text-foreground hover:bg-muted"
                          }`}
                        >
                          All Schools
                          <span className="rounded bg-muted px-1.5 py-0.5 text-[10px]">{groups.length}</span>
                        </button>
                        {schools.map((school: Record<string, unknown>) => {
                          const code = asString(school.code);
                          const active = groupSchool === code;
                          const stats = schoolStats.get(code);
                          return (
                            <button
                              key={code}
                              type="button"
                              onClick={() => {
                                setGroupSchool(code);
                                setGroupSubject("all");
                              }}
                              className={`inline-flex h-7 items-center gap-1.5 rounded-md border px-2 text-[11px] font-bold transition-colors ${
                                active
                                  ? "border-primary/50 bg-primary/10 text-primary"
                                  : "border-foreground/10 bg-background text-foreground hover:bg-muted"
                              }`}
                            >
                              {asString(school.name)}
                              <span className="rounded bg-muted px-1.5 py-0.5 text-[10px]">{stats?.groups ?? 0}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                    <div>
                      <p className="mb-1.5 text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Program</p>
                      <div className="flex flex-wrap gap-1.5">
                        <button
                          type="button"
                          onClick={() => setGroupSubject("all")}
                          className={`inline-flex h-7 items-center gap-1.5 rounded-md border px-2 text-[11px] font-bold transition-colors ${
                            groupSubject === "all"
                              ? "border-primary/50 bg-primary/10 text-primary"
                              : "border-foreground/10 bg-background text-muted-foreground hover:bg-muted hover:text-foreground"
                          }`}
                        >
                          All programs
                          <span className="rounded bg-muted px-1.5 py-0.5 text-[10px]">{contextSummary.groups}</span>
                        </button>
                        {subjectFilterOptions.map((subject) => (
                          <button
                            key={subject.name}
                            type="button"
                            onClick={() => setGroupSubject(subject.name)}
                            className={`inline-flex h-7 items-center gap-1.5 rounded-md border px-2 text-[11px] font-bold transition-colors ${
                              groupSubject === subject.name
                                ? "border-primary/50 bg-primary/10 text-primary"
                                : "border-foreground/10 bg-background text-muted-foreground hover:bg-muted hover:text-foreground"
                            }`}
                          >
                            <span className={`h-2 w-2 rounded-full ${programColor(subject.name)}`} />
                            {subject.name}
                            <span className="rounded bg-muted px-1.5 py-0.5 text-[10px]">{subject.groups}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}

              <div className="mt-2 flex min-h-0 flex-1 flex-col border-t border-foreground/8 pt-2">
                {groupDeleteError ? (
                  <div className="mb-2 rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive">
                    {groupDeleteError}
                  </div>
                ) : null}
                {filteredGroups.length === 0 ? (
                <div className="rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-8 text-center">
                  <p className="text-sm font-bold">No groups found</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {schools.length === 0
                      ? "Add a client school first, then create a group."
                      : "Try a different search, or add a group for this school."}
                  </p>
                </div>
              ) : (
                <div className="min-h-[32rem] flex-1 overflow-auto p-0.5">
                  <div className="space-y-4">
                    {filteredGroupSections.map((section) => {
                      const sectionSwatch = programColor(section.name);
                      return (
                        <section key={normalizeSubjectKey(section.name)} className="space-y-2">
                          <div className="flex items-center gap-2">
                            <span className={`h-2 w-2 shrink-0 rounded-full ${sectionSwatch}`} aria-hidden="true" />
                            <p className="truncate text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
                              {section.name}
                            </p>
                            <span className="shrink-0 rounded bg-muted px-1.5 py-0.5 text-[10px] font-bold text-muted-foreground">
                              {section.groups.length} {section.groups.length === 1 ? "group" : "groups"}
                            </span>
                            <span className="h-px min-w-6 flex-1 bg-foreground/10" aria-hidden="true" />
                          </div>
                          <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3">
                            {section.groups.map((group: Record<string, unknown>) => {
                              const id = asNumber(group.id);
                              const name = asString(group.name);
                              const subjectName = asString(group.subject_name);
                              const schoolCode = asString(group.school_code);
                              const schoolName = schoolNameByCode.get(schoolCode) || schoolCode;
                              const studentsCount = asNumber(group.students_count);
                              const disqualifiedCount = asNumber(group.disqualified_count);
                              const isActive = studentsCount > 0;
                              const swatch = programColor(subjectName);
                              const isDeleting = deletingGroupId === id;
                              return (
                                <div
                                  key={id}
                                  className="group relative rounded-xl border border-foreground/10 bg-surface shadow-card transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-card-hover"
                                >
                                  <button
                                    type="button"
                                    onClick={() => setOpenGroupId(id)}
                                    className="flex w-full flex-col p-3.5 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
                                  >
                                  <div className="flex items-start gap-3">
                                    <span
                                      className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-xs font-bold text-white ${swatch}`}
                                      aria-hidden="true"
                                    >
                                      {programInitials(subjectName)}
                                    </span>
                                    <div className="min-w-0 flex-1 pr-8">
                                      <p className="truncate text-sm font-bold leading-tight">{name}</p>
                                      <p className="truncate text-[11px] text-muted-foreground">
                                        {groupSchool === "all" ? schoolName : asString(group.code) || schoolCode}
                                      </p>
                                    </div>
                                    <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground transition-colors group-hover:text-primary" />
                                  </div>

                                  <div className="mt-3 flex items-center gap-1.5">
                                    <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${swatch}`} aria-hidden="true" />
                                    <span className="truncate text-xs font-semibold">{subjectName || "No program"}</span>
                                  </div>

                                  <div className="mt-3 flex items-center justify-between border-t border-foreground/8 pt-3">
                                    <div className="flex items-baseline gap-1.5">
                                      <span className="text-lg font-bold leading-none">{studentsCount}</span>
                                      <span className="text-[11px] text-muted-foreground">active</span>
                                      {disqualifiedCount > 0 ? (
                                        <span className="ml-1 rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-bold text-amber-700">
                                          {disqualifiedCount} disq.
                                        </span>
                                      ) : null}
                                    </div>
                                    <span
                                      className={`inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-bold uppercase ${
                                        isActive ? "bg-emerald-50 text-emerald-700" : "bg-muted text-muted-foreground"
                                      }`}
                                    >
                                      {isActive ? "Active" : "Empty"}
                                    </span>
                                  </div>
                                  </button>
                                  {!isTeacherMode ? (
                                    <button
                                      type="button"
                                      onClick={() => deleteGroup(group)}
                                      disabled={isDeleting}
                                      className="absolute right-2 top-2 flex h-8 w-8 items-center justify-center rounded-lg border border-destructive/20 bg-surface text-destructive shadow-sm transition-colors hover:bg-destructive/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-destructive/25 disabled:cursor-not-allowed disabled:opacity-50"
                                      aria-label={`Delete ${name}`}
                                      title={`Delete ${name}`}
                                    >
                                      <Trash2 className="h-3.5 w-3.5" />
                                    </button>
                                  ) : null}
                                </div>
                              );
                            })}
                          </div>
                        </section>
                      );
                    })}
                  </div>
                </div>
                )}
              </div>
            </section>
        </>
      ) : null}

    </div>
  );
}
