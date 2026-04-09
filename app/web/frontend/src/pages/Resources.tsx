import { useState } from "react";
import { BookOpen, ExternalLink, FileText, Play, X } from "lucide-react";
import { TelegramLayout, Topbar } from "@/components/TelegramLayout";

interface ResourceRow {
  id: number;
  title: string;
  description?: string;
  resource_url?: string;
  resource_file_url?: string;
  resource_file_kind?: string;
  thumbnail_url?: string;
}

interface ResourceGroup {
  resource_type_name: string;
  resources: ResourceRow[];
}

interface ResourcesPageProps {
  backUrl?: string;
  subjectName?: string;
  currentStudent?: {
    fullName?: string;
    group?: string;
  };
  groupedResources?: ResourceGroup[];
}

// ─── Video card (used in horizontal scroll row) ───────────────────────────────

function VideoCard({
  item,
  onPlay,
}: {
  item: ResourceRow;
  onPlay: (title: string, src: string) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onPlay(item.title, item.resource_file_url || "")}
      className="group flex w-36 shrink-0 snap-start flex-col overflow-hidden rounded-xl border border-foreground/10 bg-background text-left transition-[box-shadow,transform] duration-200 active:scale-[0.97] sm:w-44"
    >
      {/* Thumbnail */}
      <div className="relative flex aspect-video w-full shrink-0 items-center justify-center overflow-hidden bg-foreground/6">
        {item.thumbnail_url ? (
          <img
            src={item.thumbnail_url}
            alt={item.title}
            className="absolute inset-0 h-full w-full object-cover"
          />
        ) : null}
        <span className="relative flex h-8 w-8 items-center justify-center rounded-full bg-foreground/80 text-background transition-transform duration-200 group-hover:scale-110">
          <Play className="h-3.5 w-3.5 translate-x-px" />
        </span>
      </div>

      {/* Info */}
      <div className="flex min-w-0 flex-1 flex-col gap-0.5 p-2">
        <p className="line-clamp-2 text-[11px] font-bold leading-snug">{item.title}</p>
        {item.description ? (
          <p className="line-clamp-1 text-[10px] text-muted-foreground">{item.description}</p>
        ) : null}
      </div>
    </button>
  );
}

// ─── File / link row ──────────────────────────────────────────────────────────

function FileRow({ item }: { item: ResourceRow }) {
  const hasFile = !!item.resource_file_url;
  const hasLink = !!item.resource_url;

  return (
    <div className="flex w-full min-w-0 items-center gap-2 px-3 py-2.5 sm:px-4">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
        {hasFile ? <FileText className="h-4 w-4" /> : <ExternalLink className="h-4 w-4" />}
      </span>

      <div className="min-w-0 flex-1">
        <p className="truncate text-xs font-bold leading-tight">{item.title}</p>
        {item.description ? (
          <p className="truncate text-[10px] text-muted-foreground">{item.description}</p>
        ) : null}
      </div>

      <div className="flex shrink-0 items-center gap-1.5">
        {hasFile ? (
          <a
            href={item.resource_file_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex h-8 items-center gap-1 rounded-lg bg-foreground px-2.5 text-[10px] font-bold text-background"
          >
            <FileText className="h-3 w-3" />
            Open
          </a>
        ) : null}
        {!hasFile && hasLink ? (
          <a
            href={item.resource_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex h-8 items-center gap-1 rounded-lg border border-foreground/15 px-2.5 text-[10px] font-bold"
          >
            <ExternalLink className="h-3 w-3" />
            Open
          </a>
        ) : null}
        {hasFile && hasLink ? (
          <a
            href={item.resource_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-foreground/15"
            aria-label="Reference link"
          >
            <ExternalLink className="h-3 w-3" />
          </a>
        ) : null}
      </div>
    </div>
  );
}

// ─── Group card (no negative margins — scroll sits inside padded card edges) ──

function ResourceGroupCard({
  group,
  onPlayVideo,
}: {
  group: ResourceGroup;
  onPlayVideo: (title: string, src: string) => void;
}) {
  const videos = group.resources.filter(
    (r) => r.resource_file_url && r.resource_file_kind === "video",
  );
  const others = group.resources.filter(
    (r) => !(r.resource_file_url && r.resource_file_kind === "video"),
  );

  return (
    <div className="overflow-hidden rounded-2xl border border-foreground/10 bg-surface shadow-card">
      {/* Header */}
      <div className="flex min-w-0 items-center gap-2 px-4 pb-2 pt-3 sm:px-5 sm:pt-4">
        <BookOpen className="h-4 w-4 shrink-0 text-info" />
        <h3 className="min-w-0 flex-1 truncate text-sm font-bold">{group.resource_type_name}</h3>
        <span className="shrink-0 text-xs text-muted-foreground">
          {group.resources.length} item{group.resources.length === 1 ? "" : "s"}
        </span>
      </div>

      {/* Video horizontal scroll — padding matches card edges, no negative margins */}
      {videos.length > 0 ? (
        <div className="flex snap-x snap-mandatory gap-2 overflow-x-auto px-4 pb-3 pt-1 sm:px-5">
          {videos.map((item) => (
            <VideoCard key={item.id} item={item} onPlay={onPlayVideo} />
          ))}
          {/* trailing space so last card isn't flush with right edge */}
          <div className="w-1 shrink-0" aria-hidden="true" />
        </div>
      ) : null}

      {/* File / link list */}
      {others.length > 0 ? (
        <div className={`divide-y divide-foreground/5 ${videos.length > 0 ? "border-t border-foreground/5" : ""} pb-1`}>
          {others.map((item) => (
            <FileRow key={item.id} item={item} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ResourcesPage(props: ResourcesPageProps) {
  const [activeFilter, setActiveFilter] = useState("all");
  const [videoModal, setVideoModal] = useState<{ title: string; src: string } | null>(null);

  const groupedResources = Array.isArray(props.groupedResources) ? props.groupedResources : [];
  const totalCount = groupedResources.reduce((sum, g) => sum + g.resources.length, 0);
  const visibleGroups =
    activeFilter === "all"
      ? groupedResources
      : groupedResources.filter((_g, i) => activeFilter === `group-${i + 1}`);

  return (
    <TelegramLayout
      topbar={
        <Topbar
          backUrl={props.backUrl}
          title="Subject Resources"
          subtitle={`${props.subjectName || "Resources"} · ${totalCount} item${totalCount === 1 ? "" : "s"}`}
          rightContent={
            props.currentStudent?.fullName ? (
              <div className="hidden text-right sm:block">
                <p className="text-xs font-bold leading-tight">{props.currentStudent.fullName}</p>
                <p className="text-[10px] text-muted-foreground">{props.currentStudent.group}</p>
              </div>
            ) : null
          }
        />
      }
    >
      <div className="space-y-3 animate-in pb-6 sm:space-y-4">

        {/* Type filter — only shown when there are multiple groups */}
        {groupedResources.length > 1 ? (
          <div className="overflow-hidden rounded-2xl border border-foreground/10 bg-surface shadow-card">
            <div className="px-4 pb-3 pt-3 sm:px-5 sm:pt-4">
              <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                Filter by type
              </p>
              {/* Scroll container: overflow-x-auto, no negative margins */}
              <div className="flex snap-x snap-mandatory gap-2 overflow-x-auto pb-0.5">
                <button
                  type="button"
                  onClick={() => setActiveFilter("all")}
                  className={`inline-flex shrink-0 snap-start items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                    activeFilter === "all"
                      ? "bg-foreground text-background"
                      : "bg-muted text-foreground"
                  }`}
                >
                  All <span className="opacity-60">{totalCount}</span>
                </button>
                {groupedResources.map((group, i) => {
                  const key = `group-${i + 1}`;
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setActiveFilter(key)}
                      className={`inline-flex shrink-0 snap-start items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                        activeFilter === key
                          ? "bg-foreground text-background"
                          : "bg-muted text-foreground"
                      }`}
                    >
                      {group.resource_type_name}
                      <span className="opacity-60">{group.resources.length}</span>
                    </button>
                  );
                })}
                <div className="w-1 shrink-0" aria-hidden="true" />
              </div>
            </div>
          </div>
        ) : null}

        {/* Resource groups */}
        {visibleGroups.length ? (
          visibleGroups.map((group, i) => (
            <ResourceGroupCard
              key={activeFilter === "all" ? `g-${i}` : activeFilter}
              group={group}
              onPlayVideo={(title, src) => setVideoModal({ title, src })}
            />
          ))
        ) : (
          <div className="rounded-2xl border border-foreground/10 bg-surface p-4 shadow-card">
            <p className="text-sm text-muted-foreground">
              No resources are available for this subject yet.
            </p>
          </div>
        )}
      </div>

      {/* Video modal */}
      {videoModal ? (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-foreground/60 sm:items-center sm:p-4"
          onClick={() => setVideoModal(null)}
        >
          <div
            className="flex max-h-[96dvh] w-full flex-col overflow-hidden rounded-t-2xl bg-surface shadow-card-hover sm:max-w-3xl sm:rounded-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex min-w-0 items-center justify-between gap-3 border-b border-foreground/5 px-4 py-3">
              <h3 className="min-w-0 truncate text-sm font-bold">{videoModal.title}</h3>
              <button
                type="button"
                onClick={() => setVideoModal(null)}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg hover:bg-muted"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="w-full bg-black sm:aspect-video">
              <video
                className="h-full w-full object-contain"
                controls
                autoPlay
                playsInline
                preload="metadata"
                src={videoModal.src}
                style={{ maxHeight: "70dvh" }}
              />
            </div>
          </div>
        </div>
      ) : null}
    </TelegramLayout>
  );
}
