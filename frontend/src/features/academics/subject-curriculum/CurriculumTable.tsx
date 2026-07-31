import { useMemo, useState } from "react";
import {
  ArrowDown,
  ArrowUp,
  BookOpen,
  ExternalLink,
  FileText,
  Link2,
  Pencil,
  PlayCircle,
  RotateCcw,
  Search,
  Trash2,
} from "lucide-react";
import { Modal, ModalBody } from "@/shared/ui/Modal";
import type {
  CurriculumAsset,
  CurriculumContentBlock,
  CurriculumDetail,
  CurriculumItem,
} from "./model";
import { formatCurriculumUpdatedAt } from "./model";
import { FundamentalsGuidance } from "./FundamentalsGuidance";

function ContentBlock({ block }: { block: CurriculumContentBlock }) {
  if (block.blockType === "heading") {
    return <h3 className="text-base font-black text-foreground">{block.text}</h3>;
  }
  if (block.blockType === "bullets") {
    const rows = block.text.split("\n").map((row) => row.trim()).filter(Boolean);
    return (
      <ul className="list-disc space-y-1 pl-5 text-sm leading-6 text-foreground/85">
        {rows.map((row, index) => <li key={`${row}-${index}`}>{row}</li>)}
      </ul>
    );
  }
  if (block.blockType === "note") {
    return (
      <aside className="rounded-lg border border-info/20 bg-info/10 px-4 py-3 text-sm leading-6">
        {block.text}
      </aside>
    );
  }
  return <p className="whitespace-pre-wrap text-sm leading-6 text-foreground/85">{block.text}</p>;
}

function AssetIcon({ asset }: { asset: CurriculumAsset }) {
  if (asset.assetKind === "video") return <PlayCircle className="h-4 w-4" />;
  if (asset.assetKind === "link") return <Link2 className="h-4 w-4" />;
  return <FileText className="h-4 w-4" />;
}

function LessonDetail({
  item,
  onClose,
  useGuidanceLayout,
}: {
  item: CurriculumItem | null;
  onClose: () => void;
  useGuidanceLayout: boolean;
}) {
  if (useGuidanceLayout) {
    return (
      <Modal
        open={Boolean(item)}
        title="Fundamentals teacher guidance"
        subtitle="Planning and teaching reference"
        onClose={onClose}
        size="wide"
        mobileMode="fullscreen"
        panelClassName="bg-background"
      >
        <ModalBody className="p-0 sm:p-4">
          {item ? <FundamentalsGuidance item={item} /> : null}
        </ModalBody>
      </Modal>
    );
  }
  return (
    <Modal
      open={Boolean(item)}
      title={item ? `${item.lessonNumber} · ${item.title}` : "Lesson"}
      subtitle={item ? [item.termLabel, item.weekLabel].filter(Boolean).join(" · ") : ""}
      onClose={onClose}
      size="lg"
      mobileMode="fullscreen"
    >
      <ModalBody className="space-y-5">
        {item?.specificationPoints ? (
          <section>
            <p className="text-[0.6875rem] font-black uppercase tracking-wide text-muted-foreground">
              Specification
            </p>
            <p className="mt-1 whitespace-pre-wrap text-sm leading-6">{item.specificationPoints}</p>
          </section>
        ) : null}
        {item?.contentBlocks.length ? (
          <section className="space-y-3">
            {item.contentBlocks.map((block, index) => (
              <ContentBlock key={`${block.blockType}-${index}`} block={block} />
            ))}
          </section>
        ) : (
          <p className="rounded-lg border border-dashed border-border px-4 py-8 text-center text-sm font-semibold text-muted-foreground">
            No teaching guidance has been added to this lesson yet.
          </p>
        )}
        {item?.assets.length ? (
          <section className="space-y-2">
            <p className="text-[0.6875rem] font-black uppercase tracking-wide text-muted-foreground">
              Materials
            </p>
            {item.assets.map((asset) => {
              const href = asset.assetKind === "file" ? asset.downloadUrl : asset.externalUrl;
              return (
                <a
                  key={asset.assetId}
                  href={href}
                  target={asset.assetKind === "file" ? undefined : "_blank"}
                  rel={asset.assetKind === "file" ? undefined : "noreferrer"}
                  className="flex min-h-11 items-center gap-3 rounded-lg border border-border bg-background px-3 text-sm font-bold hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                >
                  <span className="text-primary"><AssetIcon asset={asset} /></span>
                  <span className="min-w-0 flex-1 truncate">{asset.title}</span>
                  <ExternalLink className="h-4 w-4 text-muted-foreground" />
                </a>
              );
            })}
          </section>
        ) : null}
      </ModalBody>
    </Modal>
  );
}

export function CurriculumTable({
  detail,
  loading = false,
  error = "",
  editable = false,
  busyItemId = 0,
  onEdit,
  onArchive,
  onRestore,
  onMove,
  useGuidanceLayout = false,
}: {
  detail: CurriculumDetail | null;
  loading?: boolean;
  error?: string;
  editable?: boolean;
  busyItemId?: number;
  onEdit?: (item: CurriculumItem) => void;
  onArchive?: (item: CurriculumItem) => void;
  onRestore?: (item: CurriculumItem) => void;
  onMove?: (item: CurriculumItem, direction: -1 | 1) => void;
  useGuidanceLayout?: boolean;
}) {
  const [query, setQuery] = useState("");
  const [type, setType] = useState<"all" | "lesson" | "exam">("all");
  const [selected, setSelected] = useState<CurriculumItem | null>(null);
  const rows = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return (detail?.items || []).filter((item) => {
      if (!useGuidanceLayout && type !== "all" && item.itemType !== type) return false;
      if (!normalized) return true;
      return [
        item.lessonNumber,
        item.title,
        item.specificationPoints,
        item.termLabel,
        item.weekLabel,
        item.bookPages,
        item.guidance.overview,
        item.guidance.tags.join(" "),
        item.guidance.sections.map((section) => section.title).join(" "),
      ].join(" ").toLowerCase().includes(normalized);
    });
  }, [detail?.items, query, type, useGuidanceLayout]);

  if (error) {
    return (
      <div role="alert" className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-8 text-center">
        <p className="text-sm font-black text-destructive">Could not load this curriculum</p>
        <p className="mt-1 text-sm text-muted-foreground">{error}</p>
      </div>
    );
  }
  if (loading && !detail) {
    return (
      <div className="space-y-2" aria-label="Loading curriculum">
        {[1, 2, 3, 4].map((row) => (
          <div key={row} className="h-20 animate-pulse rounded-lg bg-muted motion-reduce:animate-none" />
        ))}
      </div>
    );
  }

  return (
    <>
      <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center">
        <label className="relative min-w-0 flex-1">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <span className="sr-only">Search curriculum</span>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search curriculum"
            className="h-10 w-full rounded-lg border border-border bg-background pl-9 pr-3 text-sm font-semibold outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"
          />
        </label>
        {!useGuidanceLayout ? (
        <div className="grid grid-cols-3 rounded-lg bg-muted p-1" aria-label="Curriculum item filter">
          {(["all", "lesson", "exam"] as const).map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setType(value)}
              aria-pressed={type === value}
              className={`min-h-8 rounded-md px-3 text-xs font-black capitalize ${
                type === value ? "bg-surface text-foreground shadow-sm" : "text-muted-foreground"
              }`}
            >
              {value}
            </button>
          ))}
        </div>
        ) : null}
      </div>

      <div className="overflow-hidden rounded-xl border border-border bg-surface">
        {rows.length ? (
          <div className="divide-y divide-border">
            {rows.map((item, index) => (
              <article
                key={item.itemId}
                className={`grid gap-3 px-3 py-3 ${
                  useGuidanceLayout
                    ? "md:grid-cols-[3rem_1fr_7rem_7rem_7rem_auto]"
                    : "md:grid-cols-[5.25rem_1fr_9rem_8rem_auto]"
                } ${
                  item.itemType === "exam" ? "bg-warning/5" : ""
                }`}
              >
                {useGuidanceLayout ? (
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-xs font-black text-primary">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                ) : (
                <div>
                  <p className="text-xs font-black">{item.lessonNumber}</p>
                  <span className={`mt-1 inline-flex rounded-md px-2 py-0.5 text-[0.625rem] font-black ${
                    item.itemType === "exam" ? "bg-warning/15 text-warning" : "bg-muted text-muted-foreground"
                  }`}>
                    {item.itemType === "exam" ? "Exam" : "Lesson"}
                  </span>
                </div>
                )}
                <button
                  type="button"
                  onClick={() => setSelected(item)}
                  className="min-w-0 rounded-md text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                >
                  <p className="text-sm font-black leading-5 hover:text-primary">{item.title}</p>
                  {useGuidanceLayout && item.guidance.overview ? (
                    <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">
                      {item.guidance.overview}
                    </p>
                  ) : item.specificationPoints ? (
                    <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">
                      {item.specificationPoints}
                    </p>
                  ) : null}
                </button>
                {useGuidanceLayout ? (
                  <>
                    <div className="text-xs leading-5 text-muted-foreground">
                      <span className="font-bold text-foreground">
                        {item.guidance.sections.length}
                      </span>
                      <br />sections
                    </div>
                    <div className="text-xs leading-5 text-muted-foreground">
                      <span className="font-bold text-foreground">
                        {item.guidance.durationMinutes || "—"}
                      </span>
                      <br />minutes
                    </div>
                    <div className="text-xs leading-5 text-muted-foreground">
                      <span className="font-bold text-foreground">{item.assets.length}</span>
                      <br />materials
                    </div>
                  </>
                ) : (
                  <>
                <div className="text-xs leading-5 text-muted-foreground">
                  <span className="font-bold text-foreground">{item.termLabel || "Term not set"}</span>
                  <br />{item.weekLabel || "Week not set"}
                </div>
                <div className="text-xs leading-5 text-muted-foreground">
                  {item.bookPages || "No book pages"}
                  {item.durationHours ? <><br />{item.durationHours}</> : null}
                </div>
                  </>
                )}
                {editable ? (
                  <div className="flex items-center justify-end gap-1">
                    <button
                      type="button"
                      onClick={() => onMove?.(item, -1)}
                      disabled={index === 0 || busyItemId > 0}
                      className="flex h-9 w-9 items-center justify-center rounded-lg hover:bg-muted disabled:opacity-30"
                      aria-label={`Move ${item.title} up`}
                    ><ArrowUp className="h-4 w-4" /></button>
                    <button
                      type="button"
                      onClick={() => onMove?.(item, 1)}
                      disabled={index === detail!.items.length - 1 || busyItemId > 0}
                      className="flex h-9 w-9 items-center justify-center rounded-lg hover:bg-muted disabled:opacity-30"
                      aria-label={`Move ${item.title} down`}
                    ><ArrowDown className="h-4 w-4" /></button>
                    <button
                      type="button"
                      onClick={() => onEdit?.(item)}
                      disabled={busyItemId > 0}
                      className="flex h-9 w-9 items-center justify-center rounded-lg hover:bg-muted disabled:opacity-40"
                      aria-label={`Edit ${item.title}`}
                    ><Pencil className="h-4 w-4" /></button>
                    <button
                      type="button"
                      onClick={() => onArchive?.(item)}
                      disabled={busyItemId > 0}
                      className="flex h-9 w-9 items-center justify-center rounded-lg text-destructive hover:bg-destructive/10 disabled:opacity-40"
                      aria-label={`Archive ${item.title}`}
                    ><Trash2 className="h-4 w-4" /></button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => setSelected(item)}
                    className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border border-border px-3 text-xs font-black hover:bg-muted"
                  >
                    <BookOpen className="h-4 w-4" />Open
                  </button>
                )}
              </article>
            ))}
          </div>
        ) : (
          <div className="px-4 py-14 text-center">
            <BookOpen className="mx-auto h-8 w-8 text-muted-foreground/60" />
            <p className="mt-3 text-sm font-black">No curriculum rows found</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {query || type !== "all" ? "Change the search or filter." : "Lessons will appear here when they are added."}
            </p>
          </div>
        )}
      </div>

      {editable && detail?.archivedItems.length ? (
        <details className="mt-3 rounded-xl border border-border bg-surface">
          <summary className="cursor-pointer px-4 py-3 text-sm font-black">
            Archived lessons · {detail.archivedItems.length}
          </summary>
          <div className="divide-y divide-border border-t border-border">
            {detail.archivedItems.map((item) => (
              <div key={item.itemId} className="flex items-center gap-3 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-black">{item.lessonNumber} · {item.title}</p>
                  <p className="text-xs text-muted-foreground">
                    Updated {formatCurriculumUpdatedAt(item.updatedAt) || "recently"}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => onRestore?.(item)}
                  disabled={busyItemId > 0}
                  className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-border px-3 text-xs font-black hover:bg-muted disabled:opacity-40"
                ><RotateCcw className="h-4 w-4" />Restore</button>
              </div>
            ))}
          </div>
        </details>
      ) : null}
      <LessonDetail
        item={selected}
        onClose={() => setSelected(null)}
        useGuidanceLayout={useGuidanceLayout}
      />
    </>
  );
}
