import {
  ArrowDown,
  ArrowUp,
  List,
  MessageSquareText,
  Plus,
  StickyNote,
  Trash2,
} from "lucide-react";
import type {
  CurriculumBlockType,
  CurriculumContentBlock,
} from "./model";

const ALLOWED_BLOCK_TYPES: Array<{
  blockType: Exclude<CurriculumBlockType, "heading">;
  label: string;
  icon: typeof MessageSquareText;
}> = [
  { blockType: "paragraph", label: "Text", icon: MessageSquareText },
  { blockType: "bullets", label: "Bullet list", icon: List },
  { blockType: "note", label: "Teaching note", icon: StickyNote },
];

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

export function GuidanceBlockEditor({
  blocks,
  emptyLabel,
  onChange,
}: {
  blocks: CurriculumContentBlock[];
  emptyLabel: string;
  onChange: (blocks: CurriculumContentBlock[]) => void;
}) {
  return (
    <div className="space-y-2">
      {blocks.map((block, index) => (
        <article
          key={index}
          className="rounded-xl border border-border bg-background p-2.5"
        >
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <select
              value={block.blockType}
              onChange={(event) => {
                const next = [...blocks];
                next[index] = {
                  ...block,
                  blockType: event.target.value as Exclude<CurriculumBlockType, "heading">,
                };
                onChange(next);
              }}
              className="h-9 rounded-lg border border-border bg-surface px-2 text-xs font-black outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"
              aria-label={`Content type for block ${index + 1}`}
            >
              {ALLOWED_BLOCK_TYPES.map(({ blockType, label }) => (
                <option key={blockType} value={blockType}>{label}</option>
              ))}
            </select>
            <span className="flex-1 text-right text-[0.625rem] font-black uppercase tracking-wide text-muted-foreground">
              Block {index + 1}
            </span>
            <button
              type="button"
              disabled={index === 0}
              onClick={() => onChange(moveBlock(blocks, index, -1))}
              className="flex h-9 w-9 items-center justify-center rounded-lg hover:bg-muted disabled:opacity-30"
              aria-label={`Move block ${index + 1} up`}
            >
              <ArrowUp className="h-4 w-4" />
            </button>
            <button
              type="button"
              disabled={index === blocks.length - 1}
              onClick={() => onChange(moveBlock(blocks, index, 1))}
              className="flex h-9 w-9 items-center justify-center rounded-lg hover:bg-muted disabled:opacity-30"
              aria-label={`Move block ${index + 1} down`}
            >
              <ArrowDown className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => onChange(blocks.filter((_, blockIndex) => blockIndex !== index))}
              className="flex h-9 w-9 items-center justify-center rounded-lg text-destructive hover:bg-destructive/10"
              aria-label={`Remove block ${index + 1}`}
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
          <textarea
            required
            value={block.text}
            onChange={(event) => {
              const next = [...blocks];
              next[index] = { ...block, text: event.target.value };
              onChange(next);
            }}
            rows={block.blockType === "bullets" ? 4 : 3}
            placeholder={
              block.blockType === "bullets"
                ? "One bullet per line"
                : block.blockType === "note"
                  ? "A useful warning, alternative, or teaching tip"
                  : "Write the guidance text"
            }
            className="w-full resize-y rounded-lg border border-border bg-surface px-3 py-2 text-sm leading-6 outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"
          />
        </article>
      ))}

      {!blocks.length ? (
        <p className="rounded-lg border border-dashed border-border px-3 py-5 text-center text-xs font-semibold text-muted-foreground">
          {emptyLabel}
        </p>
      ) : null}

      <div className="flex flex-wrap gap-2">
        {ALLOWED_BLOCK_TYPES.map(({ blockType, label, icon: Icon }) => (
          <button
            key={blockType}
            type="button"
            onClick={() => onChange([...blocks, { blockType, text: "" }])}
            className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-border bg-surface px-3 text-xs font-black hover:bg-muted"
          >
            <Plus className="h-3.5 w-3.5" />
            <Icon className="h-3.5 w-3.5 text-primary" />
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
