// Shared types, constants, and pure helpers for teacher records.
import { asString } from "@/shared/lib/workspace";
import { csrfHeaders } from "@/shared/lib/api";

export type TeacherTab = "academy" | "active";
export type Teacher = Record<string, unknown>;
export type ToastTone = "success" | "danger";

export const TAB_STORAGE_KEY = "msi.admin.teacherTab";
export const TABLE_PAGE_SIZE = 8;

export const tabs: Array<{ key: TeacherTab; label: string; hint: string }> = [
  { key: "academy", label: "Teacher Academy", hint: "New Academy teachers" },
  { key: "active", label: "Active Teachers", hint: "Assigned staff" },
];

export const teacherCategories = [
  { key: "junior", label: "Junior Teacher" },
  { key: "trained", label: "Trained Teacher" },
  { key: "experienced_igcse", label: "Experienced IGCSE Teacher" },
];

export const semesterStages = ["1-2", "3-4", "5-6"];

export const lessonPayrates: Record<string, Record<string, Record<number, number>>> = {
  junior: {
    "1-2": { 7: 80000, 8: 85000, 9: 90000, 10: 100000 },
    "3-4": { 7: 90000, 8: 95000, 9: 100000, 10: 110000 },
    "5-6": { 7: 100000, 8: 105000, 9: 110000, 10: 120000 },
  },
  trained: {
    "1-2": { 7: 100000, 8: 105000, 9: 110000, 10: 120000 },
    "3-4": { 7: 110000, 8: 115000, 9: 120000, 10: 130000 },
    "5-6": { 7: 120000, 8: 125000, 9: 130000, 10: 140000 },
  },
  experienced_igcse: {
    "1-2": { 7: 120000, 8: 130000, 9: 140000, 10: 150000 },
    "3-4": { 7: 140000, 8: 150000, 9: 160000, 10: 170000 },
    "5-6": { 7: 160000, 8: 170000, 9: 180000, 10: 200000 },
  },
};

export function teacherCategoryLabel(value: unknown) {
  const normalized = asString(value) || "junior";
  return teacherCategories.find((category) => category.key === normalized)?.label || "Junior Teacher";
}

export function scoreBand(value: unknown) {
  const score = Number(value);
  if (score >= 10) return 10;
  if (score >= 9) return 9;
  if (score >= 8) return 8;
  return 7;
}

export function suggestedLessonRate(category: unknown, semesterStage: unknown, performanceScore: unknown) {
  const categoryKey = asString(category) || "junior";
  const stageKey = asString(semesterStage) || "1-2";
  return lessonPayrates[categoryKey]?.[stageKey]?.[scoreBand(performanceScore)] || 0;
}

export function formatUzs(value: number) {
  return value ? `${value.toLocaleString("en-US")} UZS` : "";
}

export async function postForm(url: string, fields: Record<string, string>, csrf: string) {
  const body = new FormData();
  Object.entries(fields).forEach(([key, value]) => body.set(key, value));
  body.set("csrf_token", csrf);
  let data: Record<string, unknown> = {};
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: csrfHeaders(csrf),
      body,
    });
    try {
      data = (await res.json()) as Record<string, unknown>;
    } catch {
      data = {};
    }
    const isApiSuccess = data.status === "success" && data.data && typeof data.data === "object";
    const isApiError = data.status === "error";
    const payload = isApiSuccess ? data.data as Record<string, unknown> : data;
    return { ok: res.ok && !isApiError && data.ok !== false, data: payload };
  } catch {
    return { ok: false, data: { message: "Network error. Please try again." } };
  }
}
