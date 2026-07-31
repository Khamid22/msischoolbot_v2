import { useState, type FormEvent, type ReactNode } from "react";
import {
  FileUp,
  Link2,
  LoaderCircle,
  Paperclip,
  Save,
  Video,
} from "lucide-react";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";
import type {
  CurriculumBlockType,
  CurriculumItem,
  CurriculumItemType,
  CurriculumItemWrite,
} from "./model";

const inputClass =
  "h-10 w-full rounded-lg border border-border bg-background px-3 text-sm font-semibold outline-none focus:border-primary focus:ring-2 focus:ring-primary/15";

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label>
      <span className="mb-1 block text-[0.6875rem] font-black uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      {children}
    </label>
  );
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
  draft: CurriculumItemWrite;
  busy: boolean;
  error: string;
  onDraftChange: (draft: CurriculumItemWrite) => void;
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
      title={item ? "Edit Fundamentals lesson" : "Add Fundamentals lesson"}
      subtitle="Primary Curriculum records are never changed here."
      onClose={() => !busy && onClose()}
      size="xl"
      mobileMode="fullscreen"
      closeOnOutsideClick={!busy}
      closeOnEscape={!busy}
    >
      <form onSubmit={onSave} className="contents">
        <ModalBody className="space-y-5">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Field label="Lesson number">
              <input
                required
                value={draft.lessonNumber}
                onChange={(event) =>
                  onDraftChange({ ...draft, lessonNumber: event.target.value })
                }
                className={inputClass}
              />
            </Field>
            <Field label="Type">
              <select
                value={draft.itemType}
                onChange={(event) =>
                  onDraftChange({
                    ...draft,
                    itemType: event.target.value as CurriculumItemType,
                  })
                }
                className={inputClass}
              >
                <option value="lesson">Lesson</option>
                <option value="exam">Exam</option>
              </select>
            </Field>
            <Field label="Term">
              <input
                value={draft.termLabel}
                onChange={(event) =>
                  onDraftChange({ ...draft, termLabel: event.target.value })
                }
                className={inputClass}
              />
            </Field>
            <Field label="Week">
              <input
                value={draft.weekLabel}
                onChange={(event) =>
                  onDraftChange({ ...draft, weekLabel: event.target.value })
                }
                className={inputClass}
              />
            </Field>
          </div>
          <Field label="Title">
            <input
              required
              value={draft.title}
              onChange={(event) => onDraftChange({ ...draft, title: event.target.value })}
              className={inputClass}
            />
          </Field>
          <Field label="Specification points">
            <textarea
              value={draft.specificationPoints}
              onChange={(event) =>
                onDraftChange({ ...draft, specificationPoints: event.target.value })
              }
              rows={3}
              className={`${inputClass} h-auto py-2`}
            />
          </Field>
          <div className="grid gap-3 sm:grid-cols-3">
            <Field label="Book pages">
              <input
                value={draft.bookPages}
                onChange={(event) =>
                  onDraftChange({ ...draft, bookPages: event.target.value })
                }
                className={inputClass}
              />
            </Field>
            <Field label="Lesson count">
              <input
                value={draft.lessonCount}
                onChange={(event) =>
                  onDraftChange({ ...draft, lessonCount: event.target.value })
                }
                className={inputClass}
              />
            </Field>
            <Field label="Duration">
              <input
                value={draft.durationHours}
                onChange={(event) =>
                  onDraftChange({ ...draft, durationHours: event.target.value })
                }
                className={inputClass}
              />
            </Field>
          </div>

          <section className="rounded-xl border border-border p-3">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-black">Lesson content</h3>
                <p className="text-xs text-muted-foreground">
                  Safe formatted blocks for teachers.
                </p>
              </div>
              <button
                type="button"
                onClick={() =>
                  onDraftChange({
                    ...draft,
                    contentBlocks: [
                      ...draft.contentBlocks,
                      { blockType: "paragraph", text: "" },
                    ],
                  })
                }
                className="min-h-9 rounded-lg border border-border px-3 text-xs font-black hover:bg-muted"
              >
                Add block
              </button>
            </div>
            <div className="space-y-2">
              {draft.contentBlocks.map((block, index) => (
                <div
                  key={index}
                  className="grid gap-2 rounded-lg bg-muted/45 p-2 sm:grid-cols-[9rem_1fr_auto]"
                >
                  <select
                    value={block.blockType}
                    onChange={(event) => {
                      const blocks = [...draft.contentBlocks];
                      blocks[index] = {
                        ...block,
                        blockType: event.target.value as CurriculumBlockType,
                      };
                      onDraftChange({ ...draft, contentBlocks: blocks });
                    }}
                    className={inputClass}
                  >
                    <option value="heading">Heading</option>
                    <option value="paragraph">Paragraph</option>
                    <option value="bullets">Bullets</option>
                    <option value="note">Note</option>
                  </select>
                  <textarea
                    required
                    value={block.text}
                    onChange={(event) => {
                      const blocks = [...draft.contentBlocks];
                      blocks[index] = { ...block, text: event.target.value };
                      onDraftChange({ ...draft, contentBlocks: blocks });
                    }}
                    rows={2}
                    className={`${inputClass} h-auto py-2`}
                  />
                  <button
                    type="button"
                    onClick={() =>
                      onDraftChange({
                        ...draft,
                        contentBlocks: draft.contentBlocks.filter(
                          (_, itemIndex) => itemIndex !== index,
                        ),
                      })
                    }
                    className="min-h-10 rounded-lg px-3 text-xs font-black text-destructive hover:bg-destructive/10"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          </section>

          {item ? (
            <section className="space-y-3 rounded-xl border border-border p-3">
              <div>
                <h3 className="flex items-center gap-2 text-sm font-black">
                  <Paperclip className="h-4 w-4 text-primary" />Materials
                </h3>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Add HTTPS links, videos, or private files.
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
                          onClick={() =>
                            void onArchiveAsset(asset.assetId, asset.version)
                          }
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
                  required
                  value={assetTitle}
                  onChange={(event) => setAssetTitle(event.target.value)}
                  placeholder="Title"
                  className={inputClass}
                />
                <input
                  required
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
                  {assetKind === "video" ? (
                    <Video className="h-4 w-4" />
                  ) : (
                    <Link2 className="h-4 w-4" />
                  )}
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
                  required
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
