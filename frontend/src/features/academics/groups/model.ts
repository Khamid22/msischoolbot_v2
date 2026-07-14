import { compareSubjectsByPreferredOrder, type DomainRow, type SchoolStats } from "@/features/organization/model";
import { asNumber, asString, normalizeSubjectKey } from "@/shared/lib/workspace";

export function groupContextSummary(
  groups: DomainRow[],
  schoolCode: string,
  schoolStats: Map<string, SchoolStats>,
) {
  if (schoolCode !== "all") {
    const stats = schoolStats.get(schoolCode);
    return {
      groups: stats?.groups ?? 0,
      activeStudents: stats?.activeStudents ?? 0,
      programs: stats?.programs.size ?? 0,
    };
  }
  const programs = new Set<string>();
  let activeStudents = 0;
  groups.forEach((group) => {
    activeStudents += asNumber(group.students_count);
    const subject = asString(group.subject_name);
    if (subject) programs.add(normalizeSubjectKey(subject));
  });
  return { groups: groups.length, activeStudents, programs: programs.size };
}

export function subjectFilterOptions(groups: DomainRow[], schoolCode: string) {
  const result = new Map<string, { name: string; groups: number; students: number }>();
  groups.forEach((group) => {
    if (schoolCode !== "all" && asString(group.school_code) !== schoolCode) return;
    const name = asString(group.subject_name);
    if (!name) return;
    const key = normalizeSubjectKey(name);
    const entry = result.get(key) ?? { name, groups: 0, students: 0 };
    entry.groups += 1;
    entry.students += asNumber(group.students_count);
    result.set(key, entry);
  });
  return Array.from(result.values()).sort((left, right) =>
    compareSubjectsByPreferredOrder(left.name, right.name),
  );
}

export function filteredGroupRows(
  groups: DomainRow[],
  queryValue: string,
  schoolCode: string,
  subjectName: string,
  schoolNames: Map<string, string>,
) {
  const query = queryValue.trim().toLowerCase();
  return groups.filter((group) => {
    const name = asString(group.name);
    const subject = asString(group.subject_name);
    const currentSchoolCode = asString(group.school_code);
    const schoolName = schoolNames.get(currentSchoolCode) || currentSchoolCode;
    return (
      (!query || `${name} ${subject} ${currentSchoolCode} ${schoolName}`.toLowerCase().includes(query)) &&
      (schoolCode === "all" || currentSchoolCode === schoolCode) &&
      (subjectName === "all" || subject === subjectName)
    );
  });
}

export function groupSections(groups: DomainRow[]) {
  const sections = new Map<string, { name: string; groups: DomainRow[] }>();
  groups.forEach((group) => {
    const name = asString(group.subject_name) || "No program";
    const key = normalizeSubjectKey(name);
    const section = sections.get(key) ?? { name, groups: [] };
    section.groups.push(group);
    sections.set(key, section);
  });
  return Array.from(sections.values()).sort((left, right) =>
    compareSubjectsByPreferredOrder(left.name, right.name),
  );
}
