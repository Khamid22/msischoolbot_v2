import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  ArrowDown,
  ArrowUp,
  Eye,
  LoaderCircle,
  Pencil,
  Plus,
  Save,
  Trash2,
} from "lucide-react";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";
import { FundamentalsGuidance } from "./FundamentalsGuidance";
import {
  FundamentalsLessonIdentity,
  LessonEditorField,
  lessonEditorInputClass,
} from "./FundamentalsLessonIdentity";
import { GuidanceBlockEditor } from "./GuidanceBlockEditor";
import type {
  CurriculumAsset,
  CurriculumContentBlock,
  CurriculumItem,
  CurriculumLessonDraft,
  LessonGuidanceDocument,
  LessonGuidanceSection,
} from "./model";

function stableKey(prefix: string) {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function emptySection(): LessonGuidanceSection {
  return {
    sectionKey: stableKey("section"),
    title: "",
    activityLabel: "",
    durationMinutes: 0,
    planningBlocks: [],
    teachingBlocks: [],
  };
}

function moveSection(
  sections: LessonGuidanceSection[],
  index: number,
  direction: -1 | 1,
) {
  const nextIndex = index + direction;
  if (nextIndex < 0 || nextIndex >= sections.length) return sections;
  const next = [...sections];
  [next[index], next[nextIndex]] = [next[nextIndex], next[index]];
  return next;
}

type ContentArea =
  | { kind: "before" }
  | { kind: "section"; sectionIndex: number; column: "planning" | "teaching" };

function blocksAt(
  guidance: LessonGuidanceDocument,
  area: ContentArea,
): CurriculumContentBlock[] {
  if (area.kind === "before") return guidance.beforeTeaching;
  const section = guidance.sections[area.sectionIndex];
  return area.column === "planning" ? section.planningBlocks : section.teachingBlocks;
}

function replaceBlocks(
  guidance: LessonGuidanceDocument,
  area: ContentArea,
  blocks: CurriculumContentBlock[],
): LessonGuidanceDocument {
  if (area.kind === "before") return { ...guidance, beforeTeaching: blocks };
  const sections = [...guidance.sections];
  const section = sections[area.sectionIndex];
  sections[area.sectionIndex] = area.column === "planning"
    ? { ...section, planningBlocks: blocks }
    : { ...section, teachingBlocks: blocks };
  return { ...guidance, sections };
}

function mediaBlock(asset: CurriculumAsset): CurriculumContentBlock {
  return {
    blockType: asset.renderKind,
    blockKey: stableKey("media"),
    text: asset.title,
    assetId: asset.assetId,
  };
}

function previewItem(draft: CurriculumLessonDraft): CurriculumItem {
  return {
    itemId: draft.itemId,
    itemOrder: 1,
    lessonNumber: "",
    itemType: "lesson",
    title: draft.title || "Untitled Fundamentals lesson",
    termLabel: "",
    weekLabel: "",
    specificationPoints: "",
    bookPages: "",
    lessonCount: "",
    durationHours: "",
    contentBlocks: [],
    guidance: draft.guidance,
    assets: draft.assets,
    status: "active",
    version: draft.baseItemVersion,
    updatedAt: draft.updatedAt,
  };
}

export function FundamentalsItemEditor({
  draft,
  busy,
  savingDraft,
  error,
  onDraftChange,
  onClose,
  onSave,
  onAddExternalAsset,
  onUploadFile,
  onDetachAsset,
  onRetryConversion,
}: {
  draft: CurriculumLessonDraft;
  busy: boolean;
  savingDraft: boolean;
  error: string;
  onDraftChange: (draft: CurriculumLessonDraft) => void;
  onClose: () => Promise<void> | void;
  onSave: (event: FormEvent) => void;
  onAddExternalAsset: (
    kind: "link" | "embed",
    title: string,
    url: string,
  ) => Promise<CurriculumLessonDraft | null>;
  onUploadFile: (
    title: string,
    file: File,
    onProgress: (percent: number) => void,
  ) => Promise<CurriculumLessonDraft | null>;
  onDetachAsset: (
    asset: CurriculumAsset,
  ) => Promise<CurriculumLessonDraft | null>;
  onRetryConversion: (
    assetId: number,
  ) => Promise<CurriculumLessonDraft | null>;
}) {
  const [mode, setMode] = useState<"edit" | "preview">("edit");
  const guidance = draft.guidance;
  const teacherPreview = useMemo(() => previewItem(draft), [draft]);

  useEffect(() => {
    const confirmUnsavedChanges = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", confirmUnsavedChanges);
    return () => window.removeEventListener("beforeunload", confirmUnsavedChanges);
  }, []);

  function updateGuidance(next: Partial<LessonGuidanceDocument>) {
    onDraftChange({ ...draft, guidance: { ...guidance, ...next } });
  }

  function updateSection(index: number, next: LessonGuidanceSection) {
    const sections = [...guidance.sections];
    sections[index] = next;
    updateGuidance({ sections });
  }

  function newestAsset(next: CurriculumLessonDraft) {
    const currentIds = new Set(draft.assets.map((asset) => asset.assetId));
    return next.assets.find((asset) => !currentIds.has(asset.assetId)) || null;
  }

  function mergeServerDraft(
    next: CurriculumLessonDraft,
    nextGuidance: LessonGuidanceDocument,
  ) {
    onDraftChange({
      ...next,
      title: draft.title,
      guidance: nextGuidance,
    });
  }

  async function uploadInto(
    area: ContentArea,
    title: string,
    file: File,
    onProgress: (percent: number) => void,
  ) {
    const next = await onUploadFile(title, file, onProgress);
    if (!next) return false;
    const asset = newestAsset(next);
    if (!asset) return false;
    mergeServerDraft(
      next,
      replaceBlocks(guidance, area, [
        ...blocksAt(guidance, area),
        mediaBlock(asset),
      ]),
    );
    return true;
  }

  async function replaceIn(
    area: ContentArea,
    existingAsset: CurriculumAsset,
    title: string,
    file: File,
    onProgress: (percent: number) => void,
  ) {
    const uploadedDraft = await onUploadFile(title, file, onProgress);
    if (!uploadedDraft) return false;
    const replacement = newestAsset(uploadedDraft);
    if (!replacement) return false;
    const detachedDraft = await onDetachAsset(existingAsset);
    if (!detachedDraft) return false;
    const nextBlocks = blocksAt(guidance, area).map((block) =>
      block.assetId === existingAsset.assetId
        ? {
            ...mediaBlock(replacement),
            blockKey: block.blockKey,
            text: block.text || replacement.title,
          }
        : block
    );
    mergeServerDraft(detachedDraft, replaceBlocks(guidance, area, nextBlocks));
    return true;
  }

  async function addExternalInto(
    area: ContentArea,
    kind: "link" | "embed",
    title: string,
    url: string,
  ) {
    const next = await onAddExternalAsset(kind, title, url);
    if (!next) return false;
    const asset = newestAsset(next);
    if (!asset) return false;
    mergeServerDraft(
      next,
      replaceBlocks(guidance, area, [
        ...blocksAt(guidance, area),
        mediaBlock(asset),
      ]),
    );
    return true;
  }

  async function detachFrom(
    area: ContentArea,
    asset: CurriculumAsset,
    nextBlocks: CurriculumContentBlock[],
  ) {
    const next = await onDetachAsset(asset);
    if (!next) return false;
    mergeServerDraft(next, replaceBlocks(guidance, area, nextBlocks));
    return true;
  }

  async function retryConversion(assetId: number) {
    const next = await onRetryConversion(assetId);
    if (next) mergeServerDraft(next, guidance);
  }

  function contentEditor(area: ContentArea, emptyLabel: string) {
    return (
      <GuidanceBlockEditor
        blocks={blocksAt(guidance, area)}
        assets={draft.assets}
        emptyLabel={emptyLabel}
        busy={busy}
        onChange={(blocks) =>
          onDraftChange({
            ...draft,
            guidance: replaceBlocks(guidance, area, blocks),
          })
        }
        onUpload={(title, file, onProgress) =>
          uploadInto(area, title, file, onProgress)
        }
        onReplace={(asset, title, file, onProgress) =>
          replaceIn(area, asset, title, file, onProgress)
        }
        onAddExternal={(kind, title, url) =>
          addExternalInto(area, kind, title, url)
        }
        onDetach={(asset, nextBlocks) => detachFrom(area, asset, nextBlocks)}
        onRetry={(assetId) => void retryConversion(assetId)}
      />
    );
  }

  return (
    <Modal
      title={draft.isNew ? "Build Fundamentals lesson" : "Edit Fundamentals lesson"}
      subtitle="Construct teacher guidance with preparation, planning, teaching, and media."
      onClose={() => !busy && void onClose()}
      size="wide"
      mobileMode="fullscreen"
      closeOnOutsideClick={false}
      closeOnEscape={!busy}
    >
      <form onSubmit={onSave} className="contents">
        <ModalBody className="space-y-5 bg-background">
          <nav
            aria-label="Lesson editor mode"
            className="mx-auto grid w-full max-w-sm grid-cols-2 rounded-xl border border-border bg-surface p-1"
          >
            <button
              type="button"
              onClick={() => setMode("edit")}
              aria-current={mode === "edit" ? "page" : undefined}
              className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-lg text-sm font-black ${
                mode === "edit" ? "bg-primary text-primary-foreground" : "text-muted-foreground"
              }`}
            >
              <Pencil className="h-4 w-4" />Edit
            </button>
            <button
              type="button"
              onClick={() => setMode("preview")}
              aria-current={mode === "preview" ? "page" : undefined}
              className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-lg text-sm font-black ${
                mode === "preview" ? "bg-primary text-primary-foreground" : "text-muted-foreground"
              }`}
            >
              <Eye className="h-4 w-4" />Teacher Preview
            </button>
          </nav>

          {mode === "preview" ? (
            <FundamentalsGuidance
              item={teacherPreview}
              onRetryConversion={(assetId) => void retryConversion(assetId)}
            />
          ) : (
            <>
              <FundamentalsLessonIdentity
                draft={draft}
                onDraftChange={onDraftChange}
              />

              <section className="rounded-xl border border-primary/15 bg-surface p-4 shadow-card">
                <div className="mb-3">
                  <p className="text-xs font-black uppercase tracking-[0.14em] text-primary">
                    Before You Teach
                  </p>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">
                    Preparation, setup, reminders, and supporting media shown above the lesson flow.
                  </p>
                </div>
                {contentEditor(
                  { kind: "before" },
                  "Add preparation text, a checklist, a note, or supporting media.",
                )}
              </section>

              <section className="space-y-3">
                <div className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-4 shadow-card sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-xs font-black uppercase tracking-[0.14em] text-primary">
                      Lesson flow
                    </p>
                    <p className="mt-1 text-xs leading-5 text-muted-foreground">
                      Each section becomes one expandable step in Teacher Guidance.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      updateGuidance({ sections: [...guidance.sections, emptySection()] })
                    }
                    className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-black text-primary-foreground"
                  >
                    <Plus className="h-4 w-4" />Add section
                  </button>
                </div>

                {guidance.sections.map((section, index) => (
                  <article
                    key={section.sectionKey}
                    className="overflow-hidden rounded-xl border border-border bg-surface shadow-card"
                  >
                    <header className="flex items-center gap-2 border-b border-border bg-muted/45 px-3 py-2.5 sm:px-4">
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-xs font-black text-primary">
                        {String(index + 1).padStart(2, "0")}
                      </span>
                      <p className="min-w-0 flex-1 truncate text-sm font-black">
                        {section.title || `Untitled section ${index + 1}`}
                      </p>
                      <button
                        type="button"
                        disabled={index === 0}
                        onClick={() =>
                          updateGuidance({
                            sections: moveSection(guidance.sections, index, -1),
                          })
                        }
                        className="flex h-9 w-9 items-center justify-center rounded-lg hover:bg-muted disabled:opacity-30"
                        aria-label={`Move section ${index + 1} up`}
                      >
                        <ArrowUp className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        disabled={index === guidance.sections.length - 1}
                        onClick={() =>
                          updateGuidance({
                            sections: moveSection(guidance.sections, index, 1),
                          })
                        }
                        className="flex h-9 w-9 items-center justify-center rounded-lg hover:bg-muted disabled:opacity-30"
                        aria-label={`Move section ${index + 1} down`}
                      >
                        <ArrowDown className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          updateGuidance({
                            sections: guidance.sections.filter(
                              (_, sectionIndex) => sectionIndex !== index,
                            ),
                          })
                        }
                        className="flex h-9 w-9 items-center justify-center rounded-lg text-destructive hover:bg-destructive/10"
                        aria-label={`Remove section ${index + 1}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </header>

                    <div className="space-y-4 p-3 sm:p-4">
                      <div className="grid gap-3 md:grid-cols-[1fr_14rem_9rem]">
                        <LessonEditorField label="Section title">
                          <input
                            required
                            value={section.title}
                            onChange={(event) =>
                              updateSection(index, {
                                ...section,
                                title: event.target.value,
                              })
                            }
                            placeholder="Starter activity"
                            className={lessonEditorInputClass}
                          />
                        </LessonEditorField>
                        <LessonEditorField label="Activity label">
                          <input
                            value={section.activityLabel}
                            onChange={(event) =>
                              updateSection(index, {
                                ...section,
                                activityLabel: event.target.value,
                              })
                            }
                            placeholder="Whole class"
                            className={lessonEditorInputClass}
                          />
                        </LessonEditorField>
                        <LessonEditorField label="Minutes">
                          <input
                            type="number"
                            min={0}
                            max={480}
                            value={section.durationMinutes || ""}
                            onChange={(event) =>
                              updateSection(index, {
                                ...section,
                                durationMinutes: Number(event.target.value) || 0,
                              })
                            }
                            placeholder="10"
                            className={lessonEditorInputClass}
                          />
                        </LessonEditorField>
                      </div>

                      <div className="grid gap-4 lg:grid-cols-2">
                        <section className="rounded-xl border border-border bg-muted/25 p-3">
                          <h4 className="text-sm font-black">Planning content</h4>
                          <p className="mb-3 mt-0.5 text-xs text-muted-foreground">
                            Preparation, explanations, files, and references.
                          </p>
                          {contentEditor(
                            { kind: "section", sectionIndex: index, column: "planning" },
                            "Add preparation, explanations, or lesson media.",
                          )}
                        </section>
                        <section className="rounded-xl border border-primary/15 bg-primary/[0.025] p-3">
                          <h4 className="text-sm font-black">Teaching content</h4>
                          <p className="mb-3 mt-0.5 text-xs text-muted-foreground">
                            Live prompts, examples, slideshows, and classroom media.
                          </p>
                          {contentEditor(
                            { kind: "section", sectionIndex: index, column: "teaching" },
                            "Add content for the teacher’s live Teaching view.",
                          )}
                        </section>
                      </div>
                    </div>
                  </article>
                ))}

                {!guidance.sections.length ? (
                  <div className="rounded-xl border border-dashed border-border bg-surface px-4 py-10 text-center">
                    <p className="text-sm font-black">No lesson sections yet</p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Add the first section to start constructing the lesson.
                    </p>
                  </div>
                ) : null}
              </section>
            </>
          )}

          {error ? (
            <p role="alert" className="text-sm font-bold text-destructive">{error}</p>
          ) : null}
          <p
            className="text-right text-xs font-semibold text-muted-foreground"
            aria-live="polite"
          >
            {savingDraft ? "Saving private draft…" : "Draft changes saved privately."}
          </p>
        </ModalBody>
        <ModalFooter className="flex justify-end gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={() => void onClose()}
            className="min-h-11 rounded-lg border border-border px-4 text-sm font-black hover:bg-muted disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={busy || !draft.title.trim()}
            className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-black text-primary-foreground disabled:opacity-50"
          >
            {busy ? (
              <LoaderCircle className="h-4 w-4 animate-spin motion-reduce:animate-none" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Save lesson
          </button>
        </ModalFooter>
      </form>
    </Modal>
  );
}
