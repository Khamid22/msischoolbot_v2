import { useEffect, useMemo, useState } from "react";
import {
  ChevronDown,
  Clock3,
  ExternalLink,
  FileText,
  Link2,
  MonitorPlay,
  PlayCircle,
  Sparkles,
  Users,
} from "lucide-react";
import type {
  CurriculumAsset,
  CurriculumContentBlock,
  CurriculumItem,
} from "./model";

interface GuidanceSection {
  sectionId: string;
  title: string;
  blocks: CurriculumContentBlock[];
}

function splitGuidance(blocks: CurriculumContentBlock[]) {
  const beforeTeaching: CurriculumContentBlock[] = [];
  const sections: GuidanceSection[] = [];
  let current: GuidanceSection | null = null;

  for (const block of blocks) {
    if (block.blockType === "heading") {
      if (current) sections.push(current);
      current = {
        sectionId: `section-${sections.length + 1}`,
        title: block.text.trim() || `Guidance section ${sections.length + 1}`,
        blocks: [],
      };
      continue;
    }
    if (current) current.blocks.push(block);
    else beforeTeaching.push(block);
  }
  if (current) sections.push(current);
  if (!sections.length && beforeTeaching.length) {
    sections.push({
      sectionId: "section-1",
      title: "Lesson guidance",
      blocks: beforeTeaching.splice(0),
    });
  }
  return { beforeTeaching, sections };
}

function guidanceTags(item: CurriculumItem) {
  return item.specificationPoints
    .split(/[\n,;]+/)
    .map((tag) => tag.trim())
    .filter(Boolean)
    .slice(0, 3);
}

function AssetIcon({ asset }: { asset: CurriculumAsset }) {
  if (asset.assetKind === "video") return <PlayCircle className="h-4 w-4" />;
  if (asset.assetKind === "link") return <Link2 className="h-4 w-4" />;
  return <FileText className="h-4 w-4" />;
}

function GuidanceBlock({
  block,
  teachingMode,
}: {
  block: CurriculumContentBlock;
  teachingMode: boolean;
}) {
  if (block.blockType === "bullets") {
    const rows = block.text.split("\n").map((row) => row.trim()).filter(Boolean);
    return (
      <ul className={`space-y-2 ${teachingMode ? "text-base leading-7" : "text-sm leading-6"}`}>
        {rows.map((row, index) => (
          <li key={`${row}-${index}`} className="flex items-start gap-3">
            <span className="mt-[0.625rem] h-1.5 w-1.5 shrink-0 rounded-sm bg-primary" />
            <span className="text-foreground/85">{row}</span>
          </li>
        ))}
      </ul>
    );
  }
  if (block.blockType === "note") {
    return (
      <aside className="rounded-xl border border-primary/20 bg-primary/5 p-4">
        <div className="flex items-center gap-2 text-primary">
          <Sparkles className="h-4 w-4" />
          <p className="text-xs font-black uppercase tracking-[0.12em]">Teaching note</p>
        </div>
        <p className={`mt-2 whitespace-pre-wrap text-foreground/85 ${
          teachingMode ? "text-base leading-7" : "text-sm leading-6"
        }`}>
          {block.text}
        </p>
      </aside>
    );
  }
  return (
    <p className={`whitespace-pre-wrap text-foreground/85 ${
      teachingMode ? "text-base leading-7" : "text-sm leading-6"
    }`}>
      {block.text}
    </p>
  );
}

export function FundamentalsGuidance({ item }: { item: CurriculumItem }) {
  const { beforeTeaching, sections } = useMemo(
    () => splitGuidance(item.contentBlocks),
    [item.contentBlocks],
  );
  const tags = useMemo(() => guidanceTags(item), [item]);
  const [teachingMode, setTeachingMode] = useState(false);
  const [openSections, setOpenSections] = useState<Set<string>>(
    () => new Set(sections[0] ? [sections[0].sectionId] : []),
  );

  useEffect(() => {
    setTeachingMode(false);
    setOpenSections(new Set(sections[0] ? [sections[0].sectionId] : []));
  }, [item.itemId, sections]);

  function setAllSections(isOpen: boolean) {
    setOpenSections(new Set(isOpen ? sections.map((section) => section.sectionId) : []));
  }

  function toggleSection(sectionId: string) {
    setOpenSections((current) => {
      const next = new Set(current);
      if (next.has(sectionId)) next.delete(sectionId);
      else next.add(sectionId);
      return next;
    });
  }

  function toggleMode() {
    setTeachingMode((current) => {
      if (!current) setAllSections(true);
      return !current;
    });
  }

  return (
    <article className="overflow-hidden rounded-2xl bg-background">
      <header className="relative overflow-hidden bg-primary px-5 py-7 text-primary-foreground sm:px-8 sm:py-9">
        <div
          className="pointer-events-none absolute inset-0 opacity-35"
          aria-hidden="true"
          style={{
            background:
              "radial-gradient(44rem 24rem at 90% -35%, hsl(var(--primary-glow) / 0.85), transparent 64%)",
          }}
        />
        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <div className="flex items-center gap-3 text-primary-foreground/75">
              <span className="h-px w-6 bg-primary-foreground/70" />
              <p className="text-xs font-black uppercase tracking-[0.16em]">Teacher Guidance</p>
            </div>
            <h2 className="mt-3 font-display text-2xl font-black tracking-tight sm:text-3xl">
              {item.title}
            </h2>
            {item.specificationPoints ? (
              <p className="mt-3 max-w-2xl text-sm leading-6 text-primary-foreground/80 sm:text-base">
                {item.specificationPoints}
              </p>
            ) : null}
            <div className="mt-4 flex flex-wrap gap-2">
              {tags.map((tag, index) => (
                <span
                  key={`${tag}-${index}`}
                  className="rounded-md border border-primary-foreground/20 bg-primary-foreground/10 px-3 py-1.5 text-[0.6875rem] font-bold"
                >
                  {tag}
                </span>
              ))}
              {[item.termLabel, item.weekLabel].filter(Boolean).map((label) => (
                <span
                  key={label}
                  className="rounded-md border border-primary-foreground/20 px-3 py-1.5 text-[0.6875rem] font-bold text-primary-foreground/75"
                >
                  {label}
                </span>
              ))}
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2 rounded-xl border border-primary-foreground/15 bg-primary-foreground/10 p-2">
            <span className={`text-xs font-black ${teachingMode ? "text-primary-foreground/55" : ""}`}>
              Planning
            </span>
            <button
              type="button"
              role="switch"
              aria-checked={teachingMode}
              aria-label={`Switch to ${teachingMode ? "planning" : "teaching"} view`}
              onClick={toggleMode}
              className={`flex h-7 w-12 items-center rounded-full border p-1 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-foreground/70 ${
                teachingMode
                  ? "justify-end border-primary-foreground/50 bg-primary-foreground/25"
                  : "justify-start border-primary-foreground/25 bg-foreground/25"
              }`}
            >
              <span className="h-4 w-4 rounded-full bg-primary-foreground shadow-sm" />
            </button>
            <span className={`text-xs font-black ${teachingMode ? "" : "text-primary-foreground/55"}`}>
              Teaching
            </span>
          </div>
        </div>
      </header>

      <div className={`space-y-5 p-4 sm:p-6 ${teachingMode ? "bg-primary/[0.025]" : ""}`}>
        {beforeTeaching.length ? (
          <section className="rounded-xl border border-primary/15 bg-surface p-4 shadow-card sm:p-5">
            <div className="flex items-center gap-2 text-primary">
              <Sparkles className="h-4 w-4" />
              <h3 className="text-xs font-black uppercase tracking-[0.14em]">Before You Teach</h3>
            </div>
            <div className="mt-3 space-y-3">
              {beforeTeaching.map((block, index) => (
                <GuidanceBlock
                  key={`${block.blockType}-${index}`}
                  block={block}
                  teachingMode={teachingMode}
                />
              ))}
            </div>
          </section>
        ) : null}

        {sections.length ? (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setAllSections(true)}
                  className="min-h-10 rounded-lg border border-border bg-surface px-3 text-xs font-black hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
                >
                  Expand all
                </button>
                <button
                  type="button"
                  onClick={() => setAllSections(false)}
                  className="min-h-10 rounded-lg border border-border bg-surface px-3 text-xs font-black hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
                >
                  Collapse all
                </button>
              </div>
              {item.durationHours ? (
                <span className="inline-flex items-center gap-2 rounded-lg border border-primary/25 bg-primary/5 px-3 py-2 text-xs font-black text-primary">
                  <Clock3 className="h-4 w-4" />
                  {item.durationHours}
                </span>
              ) : null}
            </div>

            <div className="space-y-3">
              {sections.map((section, index) => {
                const isOpen = openSections.has(section.sectionId);
                return (
                  <section
                    key={section.sectionId}
                    className="overflow-hidden rounded-xl border border-border bg-surface shadow-card"
                  >
                    <button
                      type="button"
                      aria-expanded={isOpen}
                      onClick={() => toggleSection(section.sectionId)}
                      className="flex min-h-16 w-full items-center justify-between gap-4 px-4 py-3 text-left hover:bg-muted/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/35 sm:px-5"
                    >
                      <span className="flex min-w-0 items-center gap-3">
                        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 font-display text-xs font-black text-primary">
                          {String(index + 1).padStart(2, "0")}
                        </span>
                        <span className="min-w-0">
                          <span className="block font-display text-sm font-black sm:text-base">
                            {section.title}
                          </span>
                          <span className="mt-0.5 flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
                            {teachingMode ? <MonitorPlay className="h-3.5 w-3.5" /> : <Users className="h-3.5 w-3.5" />}
                            {teachingMode ? "Teaching view" : "Teacher preparation"}
                          </span>
                        </span>
                      </span>
                      <ChevronDown
                        className={`h-5 w-5 shrink-0 text-muted-foreground transition-transform duration-200 motion-reduce:transition-none ${
                          isOpen ? "rotate-180" : ""
                        }`}
                      />
                    </button>
                    {isOpen ? (
                      <div className="space-y-4 border-t border-border/70 px-4 py-4 sm:px-5 sm:py-5">
                        {section.blocks.length ? (
                          section.blocks.map((block, blockIndex) => (
                            <GuidanceBlock
                              key={`${block.blockType}-${blockIndex}`}
                              block={block}
                              teachingMode={teachingMode}
                            />
                          ))
                        ) : (
                          <p className="text-sm font-semibold text-muted-foreground">
                            This section is ready for guidance content.
                          </p>
                        )}
                      </div>
                    ) : null}
                  </section>
                );
              })}
            </div>
          </>
        ) : (
          <section className="rounded-xl border border-dashed border-border bg-surface px-4 py-10 text-center">
            <p className="text-sm font-black">No teaching guidance has been added yet.</p>
            <p className="mt-1 text-sm text-muted-foreground">
              The Academic Director can add guidance blocks to this lesson.
            </p>
          </section>
        )}

        {item.assets.length ? (
          <section className="rounded-xl border border-border bg-surface p-4 shadow-card sm:p-5">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-primary" />
              <h3 className="text-xs font-black uppercase tracking-[0.14em]">Lesson Materials</h3>
            </div>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {item.assets.map((asset) => {
                const href = asset.assetKind === "file" ? asset.downloadUrl : asset.externalUrl;
                return (
                  <a
                    key={asset.assetId}
                    href={href}
                    target={asset.assetKind === "file" ? undefined : "_blank"}
                    rel={asset.assetKind === "file" ? undefined : "noreferrer"}
                    className="flex min-h-12 items-center gap-3 rounded-lg border border-border bg-background px-3 text-sm font-bold hover:border-primary/30 hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
                  >
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <AssetIcon asset={asset} />
                    </span>
                    <span className="min-w-0 flex-1 truncate">{asset.title}</span>
                    <ExternalLink className="h-4 w-4 shrink-0 text-muted-foreground" />
                  </a>
                );
              })}
            </div>
          </section>
        ) : null}
      </div>
    </article>
  );
}
