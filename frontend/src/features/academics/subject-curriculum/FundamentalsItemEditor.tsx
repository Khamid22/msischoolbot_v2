import { useState, type FormEvent, type ReactNode } from "react";
import {
  ArrowDown,
  ArrowUp,
  FileUp,
  Link2,
  LoaderCircle,
  Paperclip,
  Plus,
  Save,
  Trash2,
  Video,
} from "lucide-react";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";
import { GuidanceBlockEditor } from "./GuidanceBlockEditor";
import type {
  CurriculumItem,
  FundamentalsLessonWrite,
  LessonGuidanceSection,
} from "./model";

const inputClass =
  "h-10 w-full rounded-lg border border-border bg-background px-3 text-sm font-semibold outline-none focus:border-primary focus:ring-2 focus:ring-primary/15";

function Field({ label, hint, children }: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label>
      <span className="mb-1 block text-[0.6875rem] font-black uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      {children}
      {hint ? <span className="mt-1 block text-xs text-muted-foreground">{hint}</span> : null}
    </label>
  );
}

function sectionKey() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `section-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function emptySection(): LessonGuidanceSection {
  return {
    sectionKey: sectionKey(),
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

export function FundamentalsItemEditor({
  item,
  draft,
  busy,
  error,
  onDraftChange,
  onClose,
  onSave,
  onAddExternalAsset,
  onUploadFile,
  onArchiveAsset,
}: {
  item: CurriculumItem | null;
  draft: FundamentalsLessonWrite;
  busy: boolean;
  error: string;
  onDraftChange: (draft: FundamentalsLessonWrite) => void;
  onClose: () => void;
  onSave: (event: FormEvent) => void;
  onAddExternalAsset: (
    kind: "link" | "video",
    title: string,
    url: string,
  ) => Promise<boolean>;
  onUploadFile: (title: string, file: File) => Promise<boolean>;
  onArchiveAsset: (assetId: number, expectedVersion: number) => Promise<void>;
}) {
  const [assetKind, setAssetKind] = useState<"link" | "video">("link");
  const [assetTitle, setAssetTitle] = useState("");
  const [assetUrl, setAssetUrl] = useState("");
  const [fileTitle, setFileTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const guidance = draft.guidance;

  function updateGuidance(next: Partial<FundamentalsLessonWrite["guidance"]>) {
    onDraftChange({ ...draft, guidance: { ...guidance, ...next } });
  }

  function updateSection(index: number, next: LessonGuidanceSection) {
    const sections = [...guidance.sections];
    sections[index] = next;
    updateGuidance({ sections });
  }

  async function addExternalAsset() {
    const saved = await onAddExternalAsset(assetKind, assetTitle, assetUrl);
    if (saved) {
      setAssetTitle("");
      setAssetUrl("");
    }
  }

  async function uploadFile() {
    if (!file) return;
    const saved = await onUploadFile(fileTitle, file);
    if (saved) {
      setFileTitle("");
      setFile(null);
    }
  }

  return (
    <Modal
      title={item ? "Edit Fundamentals lesson" : "Build Fundamentals lesson"}
      subtitle="Construct teacher guidance with preparation, planning, teaching, and materials."
      onClose={() => !busy && onClose()}
      size="wide"
      mobileMode="fullscreen"
      closeOnOutsideClick={!busy}
      closeOnEscape={!busy}
    >
      <form onSubmit={onSave} className="contents">
        <ModalBody className="space-y-5 bg-background">
          <section className="rounded-xl border border-border bg-surface p-4 shadow-card">
            <div className="mb-4">
              <p className="text-xs font-black uppercase tracking-[0.14em] text-primary">
                Lesson identity
              </p>
              <h3 className="mt-1 text-base font-black">What will the teacher open?</h3>
            </div>
            <div className="space-y-3">
              <Field label="Lesson title">
                <input
                  required
                  value={draft.title}
                  onChange={(event) => onDraftChange({ ...draft, title: event.target.value })}
                  placeholder="Fundamentals I"
                  className={inputClass}
                />
              </Field>
              <Field
                label="Overview"
                hint="A short explanation shown in the guidance header."
              >
                <textarea
                  value={guidance.overview}
                  onChange={(event) => updateGuidance({ overview: event.target.value })}
                  rows={3}
                  placeholder="Foundational groundwork for complete beginners..."
                  className={`${inputClass} h-auto resize-y py-2 leading-6`}
                />
              </Field>
              <div className="grid gap-3 sm:grid-cols-[1fr_12rem]">
                <Field label="Tags" hint="Separate tags with commas.">
                  <input
                    value={guidance.tags.join(", ")}
                    onChange={(event) =>
                      updateGuidance({
                        tags: event.target.value
                          .split(",")
                          .map((tag) => tag.trim())
                          .filter(Boolean)
                          .slice(0, 8),
                      })
                    }
                    placeholder="Present Simple, Complete beginners"
                    className={inputClass}
                  />
                </Field>
                <Field label="Total minutes">
                  <input
                    type="number"
                    min={0}
                    max={480}
                    value={guidance.durationMinutes || ""}
                    onChange={(event) =>
                      updateGuidance({ durationMinutes: Number(event.target.value) || 0 })
                    }
                    placeholder="65"
                    className={inputClass}
                  />
                </Field>
              </div>
            </div>
          </section>

          <section className="rounded-xl border border-primary/15 bg-surface p-4 shadow-card">
            <div className="mb-3">
              <p className="text-xs font-black uppercase tracking-[0.14em] text-primary">
                Before You Teach
              </p>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                Preparation, room setup, prerequisites, and reminders shown above the lesson flow.
              </p>
            </div>
            <GuidanceBlockEditor
              blocks={guidance.beforeTeaching}
              emptyLabel="Add preparation text, a bullet list, or a teaching note."
              onChange={(beforeTeaching) => updateGuidance({ beforeTeaching })}
            />
          </section>

          <section className="space-y-3">
            <div className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-4 shadow-card sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-xs font-black uppercase tracking-[0.14em] text-primary">
                  Lesson flow
                </p>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  Each section becomes one expandable step in the teacher guidance page.
                </p>
              </div>
              <button
                type="button"
                onClick={() => updateGuidance({ sections: [...guidance.sections, emptySection()] })}
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
                <header className="flex items-center gap-3 border-b border-border bg-muted/45 px-3 py-2.5 sm:px-4">
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
                      updateGuidance({ sections: moveSection(guidance.sections, index, -1) })
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
                      updateGuidance({ sections: moveSection(guidance.sections, index, 1) })
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
                    <Field label="Section title">
                      <input
                        required
                        value={section.title}
                        onChange={(event) =>
                          updateSection(index, { ...section, title: event.target.value })
                        }
                        placeholder="Starter activity"
                        className={inputClass}
                      />
                    </Field>
                    <Field label="Activity label">
                      <input
                        value={section.activityLabel}
                        onChange={(event) =>
                          updateSection(index, {
                            ...section,
                            activityLabel: event.target.value,
                          })
                        }
                        placeholder="Whole class"
                        className={inputClass}
                      />
                    </Field>
                    <Field label="Minutes">
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
                        className={inputClass}
                      />
                    </Field>
                  </div>

                  <div className="grid gap-4 lg:grid-cols-2">
                    <section className="rounded-xl border border-border bg-muted/25 p-3">
                      <div className="mb-3">
                        <h4 className="text-sm font-black">Planning content</h4>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          Preparation and delivery guidance for the teacher.
                        </p>
                      </div>
                      <GuidanceBlockEditor
                        blocks={section.planningBlocks}
                        emptyLabel="Add the teacher’s preparation and explanation."
                        onChange={(planningBlocks) =>
                          updateSection(index, { ...section, planningBlocks })
                        }
                      />
                    </section>
                    <section className="rounded-xl border border-primary/15 bg-primary/[0.025] p-3">
                      <div className="mb-3">
                        <h4 className="text-sm font-black">Teaching content</h4>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          Clean prompts, examples, or instructions used during class.
                        </p>
                      </div>
                      <GuidanceBlockEditor
                        blocks={section.teachingBlocks}
                        emptyLabel="Add content for the teacher’s live Teaching view."
                        onChange={(teachingBlocks) =>
                          updateSection(index, { ...section, teachingBlocks })
                        }
                      />
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

          {item ? (
            <section className="space-y-3 rounded-xl border border-border bg-surface p-4 shadow-card">
              <div>
                <h3 className="flex items-center gap-2 text-sm font-black">
                  <Paperclip className="h-4 w-4 text-primary" />Lesson materials
                </h3>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Add HTTPS links, videos, or private files to the completed lesson.
                </p>
              </div>
              {item.assets.length ? (
                <ul className="space-y-1">
                  {item.assets.map((asset) => (
                    <li
                      key={asset.assetId}
                      className="flex items-center gap-2 rounded-lg bg-muted/45 px-3 py-2 text-xs font-bold"
                    >
                      <span className="min-w-0 flex-1 truncate">{asset.title}</span>
                      <span className="capitalize text-muted-foreground">{asset.assetKind}</span>
                      {asset.status === "active" ? (
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => void onArchiveAsset(asset.assetId, asset.version)}
                          className="min-h-8 rounded-md px-2 text-destructive hover:bg-destructive/10 disabled:opacity-50"
                        >
                          Archive
                        </button>
                      ) : (
                        <span className="rounded-md bg-muted px-2 py-1 text-muted-foreground">
                          Archived
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              ) : null}
              <div className="grid gap-2 sm:grid-cols-[8rem_1fr_1fr_auto]">
                <select
                  value={assetKind}
                  onChange={(event) => setAssetKind(event.target.value as "link" | "video")}
                  className={inputClass}
                >
                  <option value="link">Link</option>
                  <option value="video">Video</option>
                </select>
                <input
                  value={assetTitle}
                  onChange={(event) => setAssetTitle(event.target.value)}
                  placeholder="Material title"
                  className={inputClass}
                />
                <input
                  type="url"
                  pattern="https://.*"
                  value={assetUrl}
                  onChange={(event) => setAssetUrl(event.target.value)}
                  placeholder="https://..."
                  className={inputClass}
                />
                <button
                  type="button"
                  onClick={() => void addExternalAsset()}
                  disabled={busy || !assetTitle.trim() || !assetUrl.startsWith("https://")}
                  className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-border px-3 text-xs font-black hover:bg-muted disabled:opacity-50"
                >
                  {assetKind === "video" ? <Video className="h-4 w-4" /> : <Link2 className="h-4 w-4" />}
                  Add
                </button>
              </div>
              <div className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
                <input
                  value={fileTitle}
                  onChange={(event) => setFileTitle(event.target.value)}
                  placeholder="File title (optional)"
                  className={inputClass}
                />
                <input
                  type="file"
                  onChange={(event) => setFile(event.target.files?.[0] || null)}
                  className={`${inputClass} py-2`}
                />
                <button
                  type="button"
                  onClick={() => void uploadFile()}
                  disabled={busy || !file}
                  className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-border px-3 text-xs font-black hover:bg-muted disabled:opacity-50"
                >
                  <FileUp className="h-4 w-4" />Upload
                </button>
              </div>
            </section>
          ) : (
            <p className="rounded-lg bg-muted/45 px-3 py-2 text-xs font-semibold text-muted-foreground">
              Save the lesson first, then reopen it to attach materials.
            </p>
          )}

          {error ? (
            <p role="alert" className="text-sm font-bold text-destructive">{error}</p>
          ) : null}
        </ModalBody>
        <ModalFooter className="flex justify-end gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={onClose}
            className="min-h-11 rounded-lg border border-border px-4 text-sm font-black hover:bg-muted disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={busy}
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
