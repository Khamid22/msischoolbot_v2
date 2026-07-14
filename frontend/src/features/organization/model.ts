import { asNumber, asString, normalizeSubjectKey } from "@/shared/lib/workspace";

export type DomainRow = Record<string, unknown>;

export type SchoolStats = {
  groups: number;
  activeStudents: number;
  programs: Set<string>;
};

export function schoolNamesByCode(schools: DomainRow[]) {
  const result = new Map<string, string>();
  schools.forEach((school) => {
    const code = asString(school.code);
    if (code) result.set(code, asString(school.name) || code);
  });
  return result;
}

export function schoolStatsByCode(groups: DomainRow[]) {
  const result = new Map<string, SchoolStats>();
  groups.forEach((group) => {
    const code = asString(group.school_code);
    if (!code) return;
    const entry = result.get(code) ?? {
      groups: 0,
      activeStudents: 0,
      programs: new Set<string>(),
    };
    entry.groups += 1;
    entry.activeStudents += asNumber(group.students_count);
    const subject = asString(group.subject_name);
    if (subject) entry.programs.add(normalizeSubjectKey(subject));
    result.set(code, entry);
  });
  return result;
}

export function preferredSubjectOrder(value: unknown) {
  const key = normalizeSubjectKey(asString(value));
  if (key.includes("mathematics") || key.includes("math")) return 0;
  if (key.includes("chemistry")) return 1;
  if (key.includes("english")) return 2;
  return 3;
}

export function compareSubjectsByPreferredOrder(left: unknown, right: unknown) {
  const orderDiff = preferredSubjectOrder(left) - preferredSubjectOrder(right);
  if (orderDiff !== 0) return orderDiff;
  return asString(left).localeCompare(asString(right));
}
