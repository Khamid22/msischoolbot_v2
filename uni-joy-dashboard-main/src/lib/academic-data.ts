import { students } from "./mock-data";

export type Subject = {
  id: string;
  code: string;
  name: string;
  level: "IGCSE" | "AS" | "A2";
  teacher: string;
  groups: number;
  color: string;
};

export const subjects: Subject[] = [
  { id: "S01", code: "0580", name: "Mathematics", level: "IGCSE", teacher: "Dr. Aibek Nurtas", groups: 4, color: "#6366f1" },
  { id: "S02", code: "0625", name: "Physics", level: "IGCSE", teacher: "Marat Yessenov", groups: 3, color: "#10b981" },
  { id: "S03", code: "0620", name: "Chemistry", level: "IGCSE", teacher: "Saltanat Bek", groups: 3, color: "#f59e0b" },
  { id: "S04", code: "0610", name: "Biology", level: "IGCSE", teacher: "Aigerim Smagul", groups: 2, color: "#ef4444" },
  { id: "S05", code: "0500", name: "English First Language", level: "IGCSE", teacher: "Daniyar Omar", groups: 4, color: "#8b5cf6" },
  { id: "S06", code: "0510", name: "English Second Language", level: "IGCSE", teacher: "Aigerim Smagul", groups: 3, color: "#06b6d4" },
  { id: "S07", code: "0470", name: "History", level: "IGCSE", teacher: "Marat Yessenov", groups: 2, color: "#ec4899" },
  { id: "S08", code: "0450", name: "Business Studies", level: "IGCSE", teacher: "Dr. Aibek Nurtas", groups: 2, color: "#84cc16" },
  { id: "S09", code: "0478", name: "Computer Science", level: "IGCSE", teacher: "Saltanat Bek", groups: 3, color: "#3b82f6" },
  { id: "S10", code: "0455", name: "Economics", level: "IGCSE", teacher: "Daniyar Omar", groups: 2, color: "#f97316" },
];

export type Group = {
  id: string;
  name: string;
  subjectId: string;
  yearLevel: string;
  studentIds: string[];
};

export const groups: Group[] = [
  { id: "G-MATH-10A", name: "Math · Year 10A", subjectId: "S01", yearLevel: "Year 10", studentIds: students.slice(0, 12).map(s => s.id) },
  { id: "G-MATH-10B", name: "Math · Year 10B", subjectId: "S01", yearLevel: "Year 10", studentIds: students.slice(12, 22).map(s => s.id) },
  { id: "G-PHY-10A", name: "Physics · Year 10A", subjectId: "S02", yearLevel: "Year 10", studentIds: students.slice(0, 10).map(s => s.id) },
  { id: "G-CHEM-10A", name: "Chemistry · Year 10A", subjectId: "S03", yearLevel: "Year 10", studentIds: students.slice(2, 14).map(s => s.id) },
  { id: "G-BIO-11A", name: "Biology · Year 11A", subjectId: "S04", yearLevel: "Year 11", studentIds: students.slice(4, 16).map(s => s.id) },
  { id: "G-ENG-10A", name: "English · Year 10A", subjectId: "S05", yearLevel: "Year 10", studentIds: students.slice(0, 14).map(s => s.id) },
  { id: "G-CS-11A", name: "Computer Science · Year 11A", subjectId: "S09", yearLevel: "Year 11", studentIds: students.slice(6, 20).map(s => s.id) },
];

// Build the gradebook columns: weekly attendance + assessments
export type GradebookColumn =
  | { kind: "attendance"; id: string; label: string; date: string }
  | { kind: "score"; id: string; label: string; max: number; weight: number };

export const gradebookColumns: GradebookColumn[] = [
  { kind: "attendance", id: "a1", label: "Mon 03/03", date: "2026-03-03" },
  { kind: "attendance", id: "a2", label: "Wed 05/03", date: "2026-03-05" },
  { kind: "attendance", id: "a3", label: "Fri 07/03", date: "2026-03-07" },
  { kind: "attendance", id: "a4", label: "Mon 10/03", date: "2026-03-10" },
  { kind: "attendance", id: "a5", label: "Wed 12/03", date: "2026-03-12" },
  { kind: "score", id: "q1", label: "Quiz 1", max: 20, weight: 10 },
  { kind: "score", id: "hw1", label: "Homework 1", max: 10, weight: 5 },
  { kind: "score", id: "q2", label: "Quiz 2", max: 20, weight: 10 },
  { kind: "score", id: "mid", label: "Midterm", max: 100, weight: 30 },
  { kind: "score", id: "hw2", label: "Homework 2", max: 10, weight: 5 },
  { kind: "score", id: "proj", label: "Project", max: 50, weight: 20 },
  { kind: "score", id: "fin", label: "Final Exam", max: 100, weight: 40 },
];

export type AttendanceMark = "P" | "A" | "L" | "";

// Deterministic seeded values so the table is consistent between renders
function seed(s: string) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h);
}

export function getInitialGradebook(groupId: string) {
  const group = groups.find((g) => g.id === groupId);
  if (!group) return {};
  const cells: Record<string, Record<string, string | AttendanceMark>> = {};
  for (const sid of group.studentIds) {
    cells[sid] = {};
    for (const col of gradebookColumns) {
      const v = seed(sid + col.id);
      if (col.kind === "attendance") {
        const opts: AttendanceMark[] = ["P", "P", "P", "P", "A", "L", "P"];
        cells[sid][col.id] = opts[v % opts.length];
      } else {
        cells[sid][col.id] = String(Math.floor((v % (col.max + 1)) * 0.7 + col.max * 0.25));
      }
    }
  }
  return cells;
}
