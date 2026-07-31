export type CurriculumVariantKey = "fundamentals" | "primary";
export type CurriculumItemType = "lesson" | "exam";
export type CurriculumBlockType =
  | "instruction"
  | "heading"
  | "paragraph"
  | "bullets"
  | "checklist"
  | "note"
  | "quote"
  | "image"
  | "video"
  | "audio"
  | "document"
  | "presentation"
  | "embed"
  | "link";
export type CurriculumAssetKind = "file" | "link" | "video";
export type CurriculumAssetRenderKind =
  | "image"
  | "video"
  | "audio"
  | "document"
  | "presentation"
  | "embed"
  | "link";
export type CurriculumConversionStatus =
  | "not_required"
  | "pending"
  | "processing"
  | "ready"
  | "failed";

export interface CurriculumContentBlock {
  blockType: CurriculumBlockType;
  blockKey: string;
  text: string;
  assetId?: number;
}

export interface LessonGuidanceSection {
  sectionKey: string;
  title: string;
  activityLabel: string;
  durationMinutes: number;
  blocks: CurriculumContentBlock[];
}

export interface LessonGuidanceDocument {
  overview: string;
  tags: string[];
  durationMinutes: number;
  sections: LessonGuidanceSection[];
}

export const EMPTY_LESSON_GUIDANCE: LessonGuidanceDocument = {
  overview: "",
  tags: [],
  durationMinutes: 0,
  sections: [],
};

export interface CurriculumAsset {
  assetId: number;
  assetKind: CurriculumAssetKind;
  renderKind: CurriculumAssetRenderKind;
  title: string;
  externalUrl: string;
  previewUrl: string;
  downloadUrl: string;
  originalFileName: string;
  mimeType: string;
  sizeBytes: number;
  displayOrder: number;
  placementVersion: number;
  conversionStatus: CurriculumConversionStatus;
  conversionError: string;
  conversionAttempts: number;
  slides: CurriculumAssetRendition[];
  status: "active" | "archived";
  version: number;
}

export interface CurriculumAssetRendition {
  renditionId: number;
  slideNumber: number;
  previewUrl: string;
  mimeType: string;
  sizeBytes: number;
  width: number;
  height: number;
}

export interface CurriculumItem {
  itemId: number;
  itemOrder: number;
  lessonNumber: string;
  itemType: CurriculumItemType;
  title: string;
  termLabel: string;
  weekLabel: string;
  specificationPoints: string;
  bookPages: string;
  lessonCount: string;
  durationHours: string;
  contentBlocks: CurriculumContentBlock[];
  guidance: LessonGuidanceDocument;
  assets: CurriculumAsset[];
  status: "active" | "archived";
  version: number;
  updatedAt: string;
}

export interface CurriculumVariantSummary {
  curriculumId: number | null;
  programId: number | null;
  curriculumKey: CurriculumVariantKey;
  title: string;
  itemCount: number;
  lessonCount: number;
  examCount: number;
  version: number;
  isEditable: boolean;
  hasUpdates: boolean;
  updatedAt: string;
}

export interface SubjectCurriculumSummary {
  subjectId: number;
  subjectKey: string;
  subjectName: string;
  subjectShort: string;
  variants: CurriculumVariantSummary[];
}

export interface SubjectCurriculumCatalog {
  subjects: SubjectCurriculumSummary[];
}

export interface CurriculumDetail {
  subject: SubjectCurriculumSummary;
  variant: CurriculumVariantSummary;
  items: CurriculumItem[];
  archivedItems: CurriculumItem[];
}

export interface FundamentalsLessonWrite {
  title: string;
  guidance: LessonGuidanceDocument;
  expectedRevisionVersion: number;
}

export interface CurriculumLessonDraft {
  draftId: number;
  itemId: number;
  subjectId: number;
  state: "draft";
  title: string;
  guidance: LessonGuidanceDocument;
  assets: CurriculumAsset[];
  baseItemVersion: number;
  revisionVersion: number;
  isNew: boolean;
  updatedAt: string;
}

interface ApiEnvelope<T> {
  status?: string;
  data?: T;
  detail?: string;
  message?: string;
}

export async function curriculumApi<T>(
  url: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(url, {
    credentials: "same-origin",
    cache: "no-store",
    ...init,
  });
  const payload = (await response.json().catch(() => ({}))) as ApiEnvelope<T>;
  if (!response.ok || payload.status === "error" || payload.data === undefined) {
    throw new Error(payload.detail || payload.message || "Unable to load subject curriculum.");
  }
  return payload.data;
}

export function defaultVariant(subject?: SubjectCurriculumSummary | null): CurriculumVariantKey {
  if (subject?.variants.some((variant) => variant.curriculumKey === "fundamentals")) {
    return "fundamentals";
  }
  return "primary";
}

export function formatCurriculumUpdatedAt(value: string): string {
  const parsed = new Date(value);
  if (!value || Number.isNaN(parsed.getTime())) return "";
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Tashkent",
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
}

export function moveItemIds(
  items: CurriculumItem[],
  itemId: number,
  direction: -1 | 1,
): number[] {
  const ids = items.map((item) => item.itemId);
  const index = ids.indexOf(itemId);
  const nextIndex = index + direction;
  if (index < 0 || nextIndex < 0 || nextIndex >= ids.length) return ids;
  [ids[index], ids[nextIndex]] = [ids[nextIndex], ids[index]];
  return ids;
}
