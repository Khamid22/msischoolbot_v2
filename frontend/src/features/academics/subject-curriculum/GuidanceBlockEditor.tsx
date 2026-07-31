import { useRef, useState } from "react";
import {
  ArrowDown,
  ArrowUp,
  CheckSquare,
  ClipboardList,
  FileText,
  Heading3,
  Image,
  Link2,
  List,
  LoaderCircle,
  MessageSquareText,
  Music2,
  Plus,
  Presentation,
  Quote,
  RefreshCcw,
  StickyNote,
  Trash2,
  Video,
} from "lucide-react";
import { CurriculumMediaBlock } from "./CurriculumMediaBlock";
import type {
  CurriculumAsset,
  CurriculumBlockType,
  CurriculumContentBlock,
} from "./model";

const TEXT_BLOCK_TYPES: Array<{
  blockType: CurriculumBlockType;
  label: string;
  icon: typeof MessageSquareText;
}> = [
  { blockType: "instruction", label: "Teacher Instruction", icon: ClipboardList },
  { blockType: "heading", label: "Heading", icon: Heading3 },
  { blockType: "paragraph", label: "Text", icon: MessageSquareText },
  { blockType: "bullets", label: "Bullet list", icon: List },
  { blockType: "checklist", label: "Checklist", icon: CheckSquare },
  { blockType: "note", label: "Teaching note", icon: StickyNote },
  { blockType: "quote", label: "Quote", icon: Quote },
];

const FILE_BLOCK_TYPES: Array<{
  accept: string;
  label: string;
  icon: typeof Image;
}> = [
  { accept: ".jpg,.jpeg,.png,.webp,.gif", label: "Image", icon: Image },
  { accept: ".mp4,.mov,.m4v", label: "Video", icon: Video },
  { accept: ".mp3,.wav", label: "Audio", icon: Music2 },
  { accept: ".pdf,.doc,.docx,.txt,.csv,.zip", label: "File", icon: FileText },
  { accept: ".ppt,.pptx", label: "Slides", icon: Presentation },
];

function contentKey(prefix = "block") {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function moveBlock(
  blocks: CurriculumContentBlock[],
  index: number,
  direction: -1 | 1,
) {
  const nextIndex = index + direction;
  if (nextIndex < 0 || nextIndex >= blocks.length) return blocks;
  const next = [...blocks];
  [next[index], next[nextIndex]] = [next[nextIndex], next[index]];
  return next;
}

function ContentActions({
  index,
  count,
  onMove,
  onRemove,
}: {
  index: number;
  count: number;
  onMove: (direction: -1 | 1) => void;
  onRemove: () => void;
}) {
  return (
    <div className="ml-auto flex items-center gap-1">
      <button
        type="button"
        disabled={index === 0}
        onClick={() => onMove(-1)}
        className="flex h-9 w-9 items-center justify-center rounded-lg hover:bg-muted disabled:opacity-30"
        aria-label={`Move block ${index + 1} up`}
      >
        <ArrowUp className="h-4 w-4" />
      </button>
      <button
        type="button"
        disabled={index === count - 1}
        onClick={() => onMove(1)}
        className="flex h-9 w-9 items-center justify-center rounded-lg hover:bg-muted disabled:opacity-30"
        aria-label={`Move block ${index + 1} down`}
      >
        <ArrowDown className="h-4 w-4" />
      </button>
      <button
        type="button"
        onClick={onRemove}
        className="flex h-9 w-9 items-center justify-center rounded-lg text-destructive hover:bg-destructive/10"
        aria-label={`Remove block ${index + 1}`}
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </div>
  );
}

export function GuidanceBlockEditor({
  blocks,
  assets = [],
  emptyLabel,
  busy = false,
  onChange,
  onUpload,
  onReplace,
  onAddExternal,
  onDetach,
  onRetry,
}: {
  blocks: CurriculumContentBlock[];
  assets?: CurriculumAsset[];
  emptyLabel: string;
  busy?: boolean;
  onChange: (blocks: CurriculumContentBlock[]) => void;
  onUpload?: (
    title: string,
    file: File,
    onProgress: (percent: number) => void,
  ) => Promise<boolean>;
  onReplace?: (
    asset: CurriculumAsset,
    title: string,
    file: File,
    onProgress: (percent: number) => void,
  ) => Promise<boolean>;
  onAddExternal?: (
    renderKind: "link" | "embed",
    title: string,
    url: string,
  ) => Promise<boolean>;
  onDetach?: (
    asset: CurriculumAsset,
    nextBlocks: CurriculumContentBlock[],
  ) => Promise<boolean>;
  onRetry?: (assetId: number) => void;
}) {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [externalKind, setExternalKind] = useState<"link" | "embed" | null>(null);
  const [externalTitle, setExternalTitle] = useState("");
  const [externalUrl, setExternalUrl] = useState("");
  const fileTitleRef = useRef("");

  function updateBlock(index: number, nextBlock: CurriculumContentBlock) {
    const next = [...blocks];
    next[index] = nextBlock;
    onChange(next);
  }

  async function upload(file: File) {
    if (!onUpload) return;
    setUploading(true);
    setUploadProgress(0);
    try {
      await onUpload(
        fileTitleRef.current || file.name,
        file,
        setUploadProgress,
      );
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  }

  async function replace(asset: CurriculumAsset, file: File) {
    if (!onReplace) return;
    setUploading(true);
    setUploadProgress(0);
    try {
      await onReplace(
        asset,
        fileTitleRef.current || asset.title || file.name,
        file,
        setUploadProgress,
      );
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  }

  async function addExternal() {
    if (!onAddExternal || !externalKind) return;
    setUploading(true);
    try {
      const added = await onAddExternal(externalKind, externalTitle, externalUrl);
      if (added) {
        setExternalKind(null);
        setExternalTitle("");
        setExternalUrl("");
      }
    } finally {
      setUploading(false);
    }
  }

  async function removeBlock(index: number, asset?: CurriculumAsset) {
    if (asset && onDetach) {
      const nextBlocks = blocks.filter((_, blockIndex) => blockIndex !== index);
      await onDetach(asset, nextBlocks);
      return;
    }
    onChange(blocks.filter((_, blockIndex) => blockIndex !== index));
  }

  return (
    <div className="space-y-2">
      {blocks.map((block, index) => {
        const asset = block.assetId
          ? assets.find((candidate) => candidate.assetId === block.assetId)
          : undefined;
        const isMedia = Boolean(block.assetId);
        return (
          <article
            key={block.blockKey || `${block.blockType}-${index}`}
            className={`rounded-xl border p-2.5 ${
              block.blockType === "instruction"
                ? "border-primary/25 bg-primary/[0.035]"
                : "border-border bg-background"
            }`}
          >
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <span className="rounded-md bg-muted px-2 py-1 text-[0.625rem] font-black uppercase tracking-wide text-muted-foreground">
                {isMedia
                  ? asset?.renderKind || "Media"
                  : block.blockType === "instruction"
                    ? "Teacher Instruction"
                    : block.blockType}
              </span>
              <span className="text-[0.625rem] font-black uppercase tracking-wide text-muted-foreground">
                Block {index + 1}
              </span>
              <ContentActions
                index={index}
                count={blocks.length}
                onMove={(direction) => onChange(moveBlock(blocks, index, direction))}
                onRemove={() => void removeBlock(index, asset)}
              />
            </div>

            {asset ? (
              <div className="space-y-2">
                <CurriculumMediaBlock asset={asset} block={block} onRetry={onRetry} />
                <label className="block">
                  <span className="mb-1 block text-[0.625rem] font-black uppercase tracking-wide text-muted-foreground">
                    Caption or accessible description
                  </span>
                  <input
                    value={block.text}
                    onChange={(event) =>
                      updateBlock(index, { ...block, text: event.target.value })
                    }
                    className="h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"
                  />
                </label>
                {onReplace && asset.assetKind === "file" ? (
                  <label
                    className={`inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-lg border border-border bg-surface px-3 text-xs font-black hover:bg-muted ${
                      busy || uploading ? "pointer-events-none opacity-50" : ""
                    }`}
                  >
                    <RefreshCcw className="h-4 w-4 text-primary" />
                    Replace file
                    <input
                      type="file"
                      accept=".jpg,.jpeg,.png,.webp,.gif,.mp4,.mov,.m4v,.mp3,.wav,.pdf,.doc,.docx,.ppt,.pptx,.txt,.csv,.zip"
                      className="sr-only"
                      disabled={busy || uploading}
                      onChange={(event) => {
                        const file = event.target.files?.[0];
                        if (file) void replace(asset, file);
                        event.currentTarget.value = "";
                      }}
                    />
                  </label>
                ) : null}
              </div>
            ) : isMedia ? (
              <p role="alert" className="rounded-lg bg-destructive/5 p-3 text-xs font-bold text-destructive">
                This material is no longer attached. Remove the block or reload the draft.
              </p>
            ) : (
              <textarea
                required
                value={block.text}
                onChange={(event) =>
                  updateBlock(index, { ...block, text: event.target.value })
                }
                rows={
                  block.blockType === "heading"
                    ? 2
                    : block.blockType === "paragraph" || block.blockType === "instruction"
                      ? 4
                      : 3
                }
                placeholder={
                  block.blockType === "instruction"
                    ? "Write the private instruction the teacher needs while planning"
                    : block.blockType === "bullets" || block.blockType === "checklist"
                    ? "One item per line"
                    : block.blockType === "note"
                      ? "A useful warning, alternative, or teaching tip"
                      : block.blockType === "quote"
                        ? "A quotation or phrase to highlight"
                        : block.blockType === "heading"
                          ? "Section heading"
                          : "Write the guidance content"
                }
                className="w-full resize-y rounded-lg border border-border bg-surface px-3 py-2 text-sm leading-6 outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"
              />
            )}
          </article>
        );
      })}

      {!blocks.length ? (
        <p className="rounded-lg border border-dashed border-border px-3 py-5 text-center text-xs font-semibold text-muted-foreground">
          {emptyLabel}
        </p>
      ) : null}

      <div className="rounded-xl border border-border bg-muted/25 p-2.5">
        <p className="mb-2 text-[0.625rem] font-black uppercase tracking-[0.12em] text-muted-foreground">
          Add content
        </p>
        <div className="flex flex-wrap gap-2">
          {TEXT_BLOCK_TYPES.map(({ blockType, label, icon: Icon }) => (
            <button
              key={blockType}
              type="button"
              onClick={() =>
                onChange([
                  ...blocks,
                  { blockType, blockKey: contentKey(), text: "" },
                ])
              }
              className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-border bg-surface px-3 text-xs font-black hover:bg-muted"
            >
              <Plus className="h-3.5 w-3.5" />
              <Icon className="h-3.5 w-3.5 text-primary" />
              {label}
            </button>
          ))}
        </div>

        {onUpload || onAddExternal ? (
          <>
            <p className="mb-2 mt-3 text-[0.625rem] font-black uppercase tracking-[0.12em] text-muted-foreground">
              Add media
            </p>
            <input
              aria-label="Optional material title"
              placeholder="Material title (optional)"
              onChange={(event) => {
                fileTitleRef.current = event.target.value;
              }}
              className="mb-2 h-9 w-full rounded-lg border border-border bg-surface px-3 text-xs outline-none focus:border-primary"
            />
            <div className="flex flex-wrap gap-2">
              {onUpload
                ? FILE_BLOCK_TYPES.map(({ accept, label, icon: Icon }) => (
                    <label
                      key={label}
                      className={`inline-flex min-h-9 cursor-pointer items-center gap-1.5 rounded-lg border border-border bg-surface px-3 text-xs font-black hover:bg-muted ${
                        busy || uploading ? "pointer-events-none opacity-50" : ""
                      }`}
                    >
                      {uploading ? (
                        <LoaderCircle className="h-3.5 w-3.5 animate-spin motion-reduce:animate-none" />
                      ) : (
                        <Plus className="h-3.5 w-3.5" />
                      )}
                      <Icon className="h-3.5 w-3.5 text-primary" />
                      {label}
                      <input
                        type="file"
                        accept={accept}
                        className="sr-only"
                        disabled={busy || uploading}
                        onChange={(event) => {
                          const file = event.target.files?.[0];
                          if (file) void upload(file);
                          event.currentTarget.value = "";
                        }}
                      />
                    </label>
                  ))
                : null}
              {onAddExternal ? (
                <>
                  <button
                    type="button"
                    onClick={() => setExternalKind("embed")}
                    className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-border bg-surface px-3 text-xs font-black hover:bg-muted"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    <Video className="h-3.5 w-3.5 text-primary" />Embed
                  </button>
                  <button
                    type="button"
                    onClick={() => setExternalKind("link")}
                    className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-border bg-surface px-3 text-xs font-black hover:bg-muted"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    <Link2 className="h-3.5 w-3.5 text-primary" />Link
                  </button>
                </>
              ) : null}
            </div>
            {uploading ? (
              <div className="mt-3" aria-live="polite">
                <div className="mb-1 flex justify-between text-[0.625rem] font-black uppercase tracking-wide text-muted-foreground">
                  <span>Uploading material</span>
                  <span>{uploadProgress}%</span>
                </div>
                <div
                  className="h-1.5 overflow-hidden rounded-full bg-muted"
                  role="progressbar"
                  aria-label="Material upload progress"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={uploadProgress}
                >
                  <span
                    className="block h-full bg-primary transition-[width] motion-reduce:transition-none"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            ) : null}
          </>
        ) : null}

        {externalKind ? (
          <div className="mt-3 grid gap-2 rounded-lg border border-primary/15 bg-surface p-3 sm:grid-cols-[1fr_1.4fr_auto]">
            <input
              value={externalTitle}
              onChange={(event) => setExternalTitle(event.target.value)}
              placeholder="Title"
              className="h-10 rounded-lg border border-border px-3 text-sm outline-none focus:border-primary"
            />
            <input
              type="url"
              value={externalUrl}
              onChange={(event) => setExternalUrl(event.target.value)}
              placeholder="https://..."
              className="h-10 rounded-lg border border-border px-3 text-sm outline-none focus:border-primary"
            />
            <div className="flex gap-2">
              <button
                type="button"
                disabled={
                  busy
                  || uploading
                  || !externalTitle.trim()
                  || !externalUrl.startsWith("https://")
                }
                onClick={() => void addExternal()}
                className="min-h-10 rounded-lg bg-primary px-3 text-xs font-black text-primary-foreground disabled:opacity-50"
              >
                Add
              </button>
              <button
                type="button"
                onClick={() => setExternalKind(null)}
                className="min-h-10 rounded-lg border border-border px-3 text-xs font-black"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
