import { useEffect, useRef, useState } from "react";
import { BookOpen, ExternalLink, FileText, Link, Loader2, MessageSquare, Play, Send, X, ChevronRight } from "lucide-react";
import { AdminEmbedLayout, isAdminEmbedMode } from "@/shared/ui/AdminEmbedLayout";
import { TelegramLayout, Topbar } from "@/shared/ui/TelegramLayout";

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
  currentStudent?: { fullName?: string; group?: string };
  groupedResources?: ResourceGroup[];
  embedMode?: string;
}

interface ResourceModalState {
  title: string;
  videoSrc?: string;
  fileUrl?: string;
  linkUrl?: string;
  description?: string;
  resourceId: number;
}

interface Comment {
  id: number;
  authorName: string;
  body: string;
  createdAt: string;
}

function isVideo(item: ResourceRow) {
  return Boolean(item.resource_file_url && item.resource_file_kind === "video");
}

function buildModal(item: ResourceRow): ResourceModalState {
  return {
    title: item.title,
    videoSrc: isVideo(item) ? item.resource_file_url : undefined,
    fileUrl: item.resource_file_url || undefined,
    linkUrl: item.resource_url || undefined,
    description: item.description,
    resourceId: item.id,
  };
}

function CommentsSection({ resourceId }: { resourceId: number }) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [draft, setDraft] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetch(`/api/resources/${resourceId}/comments`)
      .then((r) => r.json())
      .then((data) => { if (!cancelled) setComments(Array.isArray(data.comments) ? data.comments : []); })
      .catch(() => { if (!cancelled) setComments([]); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [resourceId]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const body = draft.trim();
    if (!body || submitting) return;
    setSubmitting(true);
    setSubmitError("");
    try {
      const res = await fetch(`/api/resources/${resourceId}/comments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body }),
      });
      const data = await res.json();
      if (!res.ok) {
        setSubmitError(data.error || "Could not post comment.");
      } else {
        setComments((prev) => [...prev, data.comment]);
        setDraft("");
        setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
      }
    } catch {
      setSubmitError("Network error. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="px-4 pb-4 pt-3 sm:px-5">
      <div className="mb-3 flex items-center gap-1.5">
        <MessageSquare className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
          Comments{comments.length > 0 ? ` · ${comments.length}` : ""}
        </span>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 py-2 text-muted-foreground">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          <span className="text-xs">Loading comments…</span>
        </div>
      ) : comments.length === 0 ? (
        <p className="py-1 text-xs text-muted-foreground">No comments yet. Be the first!</p>
      ) : (
        <div className="mb-3 space-y-3">
          {comments.map((c) => (
            <div key={c.id} className="flex gap-2.5">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted text-[10px] font-bold uppercase text-muted-foreground">
                {c.authorName.charAt(0)}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline gap-1.5">
                  <span className="text-[11px] font-bold leading-tight">{c.authorName}</span>
                  <span className="text-[10px] text-muted-foreground">{c.createdAt}</span>
                </div>
                <p className="mt-0.5 text-xs leading-relaxed">{c.body}</p>
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex items-end gap-2">
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(e as unknown as React.FormEvent); }
          }}
          placeholder="Write a comment…"
          rows={2}
          maxLength={500}
          className="min-h-[2.5rem] flex-1 resize-none rounded-xl border border-foreground/10 bg-muted px-3 py-2 text-xs outline-none placeholder:text-muted-foreground focus:border-foreground/30"
        />
        <button
          type="submit"
          disabled={!draft.trim() || submitting}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-foreground text-background disabled:opacity-40"
          aria-label="Post comment"
        >
          {submitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
        </button>
      </form>
      {submitError ? <p className="mt-1.5 text-[10px] text-destructive">{submitError}</p> : null}
    </div>
  );
}

function ResourceCard({
  item,
  onOpen,
}: {
  item: ResourceRow;
  onOpen: (modal: ResourceModalState) => void;
}) {
  const video = isVideo(item);
  const hasThumb = !!item.thumbnail_url;

  const icon = video
    ? <Play className="h-4 w-4 translate-x-px" />
    : item.resource_file_url
    ? <FileText className="h-4 w-4" />
    : <Link className="h-4 w-4" />;

  const badge = video ? "Video" : item.resource_file_url ? "File" : "Link";

  return (
    <button
      type="button"
      onClick={() => onOpen(buildModal(item))}
      className="group flex w-44 shrink-0 snap-start flex-col overflow-hidden rounded-xl border border-foreground/10 bg-background text-left transition-[box-shadow,transform] duration-200 active:scale-[0.97] sm:w-56"
    >
      <div className="relative flex aspect-video w-full shrink-0 items-center justify-center overflow-hidden bg-foreground/6">
        {hasThumb ? (
          <img src={item.thumbnail_url} alt={item.title} className="absolute inset-0 h-full w-full object-cover" />
        ) : null}
        <span className="relative flex h-9 w-9 items-center justify-center rounded-full bg-foreground/80 text-background transition-transform duration-200 group-hover:scale-110">
          {icon}
        </span>
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-1 p-2.5">
        <p className="line-clamp-2 text-xs font-bold leading-snug">{item.title}</p>
        <p className="mt-auto text-[9px] font-bold uppercase tracking-wider text-muted-foreground/60">{badge}</p>
      </div>
    </button>
  );
}

function ResourceGroupCard({
  group,
  onOpen,
}: {
  group: ResourceGroup;
  onOpen: (modal: ResourceModalState) => void;
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-foreground/10 bg-surface shadow-card">
      <div className="flex min-w-0 items-center gap-2 px-4 pb-2 pt-3 sm:px-5 sm:pt-4">
        <BookOpen className="h-4 w-4 shrink-0 text-info" />
        <h3 className="min-w-0 flex-1 text-sm font-bold">{group.resource_type_name}</h3>
        <span className="shrink-0 text-xs text-muted-foreground">
          {group.resources.length} item{group.resources.length === 1 ? "" : "s"}
        </span>
      </div>
      {group.resources.length > 0 ? (
        <div className="flex snap-x snap-mandatory gap-2.5 overflow-x-auto px-4 pb-3 pt-1 sm:px-5">
          {group.resources.map((item) => (
            <ResourceCard key={item.id} item={item} onOpen={onOpen} />
          ))}
          <div className="w-1 shrink-0" aria-hidden="true" />
        </div>
      ) : null}
    </div>
  );
}

function ResourceTableGroup({
  group,
  onOpen,
}: {
  group: ResourceGroup;
  onOpen: (modal: ResourceModalState) => void;
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-foreground/10 bg-surface shadow-card">
      <div className="flex min-w-0 items-center gap-2 px-4 pb-2 pt-3 sm:px-5 sm:pt-4">
        <BookOpen className="h-4 w-4 shrink-0 text-info" />
        <h3 className="min-w-0 flex-1 text-sm font-bold">{group.resource_type_name}</h3>
        <span className="shrink-0 text-xs text-muted-foreground">
          {group.resources.length} item{group.resources.length === 1 ? "" : "s"}
        </span>
      </div>
      {group.resources.length > 0 ? (
        <div className="max-h-[70dvh] overflow-auto px-0 pb-3">
          <table className="w-full min-w-[380px] text-left">
            <thead className="sticky top-0 z-20 bg-surface shadow-[0_1px_0_hsl(var(--foreground)/0.08)]">
              <tr className="border-b border-foreground/5">
                <th className="px-4 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground sm:px-5">Title</th>
                <th className="px-4 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground sm:px-5">Type</th>
                <th className="px-4 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground sm:px-5"></th>
              </tr>
            </thead>
            <tbody>
              {group.resources.map((item) => {
                const video = isVideo(item);
                const badge = video ? "Video" : item.resource_file_url ? "File" : "Link";
                const icon = video
                  ? <Play className="h-3.5 w-3.5 translate-x-px" />
                  : item.resource_file_url
                  ? <FileText className="h-3.5 w-3.5" />
                  : <Link className="h-3.5 w-3.5" />;
                return (
                  <tr
                    key={item.id}
                    className="group cursor-pointer border-b border-foreground/5 transition-colors last:border-0 hover:bg-foreground/4"
                    onClick={() => onOpen(buildModal(item))}
                  >
                    <td className="px-4 py-2.5 sm:px-5">
                      <div className="flex items-center gap-2.5">
                        {item.thumbnail_url ? (
                          <img src={item.thumbnail_url} alt={item.title} className="h-8 w-8 shrink-0 rounded-lg object-cover" />
                        ) : (
                          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-foreground/8 text-foreground/60">
                            {icon}
                          </span>
                        )}
                        <span className="min-w-0 text-xs font-semibold leading-snug line-clamp-2">{item.title}</span>
                      </div>
                    </td>
                    <td className="px-4 py-2.5 sm:px-5">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{badge}</span>
                    </td>
                    <td className="px-4 py-2.5 text-right sm:px-5">
                      <ChevronRight className="ml-auto h-4 w-4 text-muted-foreground/50 transition-transform group-hover:translate-x-0.5" />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}

const fullscreenInsetStyle = {
  paddingTop: "var(--app-top-inset)",
  paddingRight: "var(--app-right-inset)",
  paddingBottom: "var(--app-bottom-inset)",
  paddingLeft: "var(--app-left-inset)",
} as const;

export default function ResourcesPage(props: ResourcesPageProps) {
  const [activeFilter, setActiveFilter] = useState("all");
  const [modal, setModal] = useState<ResourceModalState | null>(null);

  const groupedResources = Array.isArray(props.groupedResources) ? props.groupedResources : [];
  const totalCount = groupedResources.reduce((sum, g) => sum + g.resources.length, 0);
  const visibleGroups =
    activeFilter === "all"
      ? groupedResources
      : groupedResources.filter((_g, i) => activeFilter === `group-${i + 1}`);
  const isAdminEmbed = isAdminEmbedMode(props.embedMode);
  const subtitle = `${props.subjectName || "Resources"} · ${totalCount} item${totalCount === 1 ? "" : "s"}`;

  const pageContent = (
    <>
      <div className="animate-in space-y-3 pb-6 sm:space-y-4">
        {groupedResources.length > 1 ? (
          <div className="overflow-hidden rounded-2xl border border-foreground/10 bg-surface shadow-card">
            <div className="px-4 pb-3 pt-3 sm:px-5 sm:pt-4">
              <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Filter by type</p>
              <div className="flex snap-x snap-mandatory gap-2 overflow-x-auto pb-0.5">
                <button
                  type="button"
                  onClick={() => setActiveFilter("all")}
                  className={`inline-flex shrink-0 snap-start items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                    activeFilter === "all" ? "bg-foreground text-background" : "bg-muted text-foreground"
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
                        activeFilter === key ? "bg-foreground text-background" : "bg-muted text-foreground"
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
        {visibleGroups.length ? (
          visibleGroups.map((group, i) => (
            activeFilter === "all" ? (
              <ResourceGroupCard
                key={`g-${i}`}
                group={group}
                onOpen={setModal}
              />
            ) : (
              <ResourceTableGroup
                key={activeFilter}
                group={group}
                onOpen={setModal}
              />
            )
          ))
        ) : (
          <div className="rounded-2xl border border-foreground/10 bg-surface p-4 shadow-card">
            <p className="text-sm text-muted-foreground">No resources are available for this subject yet.</p>
          </div>
        )}
      </div>
      {modal ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-2 sm:p-4"
          style={fullscreenInsetStyle}
          onClick={() => setModal(null)}
        >
          <div
            className="flex w-full max-w-2xl max-h-[82dvh] flex-col overflow-hidden rounded-2xl bg-surface shadow-card-hover sm:max-h-[88dvh]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-foreground/5 px-4 py-3">
              <h3 className="min-w-0 truncate text-sm font-bold">{modal.title}</h3>
              <button type="button" onClick={() => setModal(null)}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg hover:bg-muted">
                <X className="h-4 w-4" />
              </button>
            </div>
            {modal.videoSrc ? (
              <div className="w-full shrink-0 bg-black">
                <video
                  className="h-full w-full object-contain"
                  controls autoPlay playsInline preload="metadata"
                  src={modal.videoSrc}
                  style={{ maxHeight: "40dvh" }}
                />
              </div>
            ) : null}
            <div className="min-h-0 flex-1 overflow-y-auto">
              {(modal.fileUrl || modal.linkUrl) ? (
                <div className="border-b border-foreground/5 px-4 py-3 sm:px-5">
                  <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Open</p>
                  <div className="flex flex-wrap gap-2">
                    {modal.fileUrl && !modal.videoSrc ? (
                      <a href={modal.fileUrl} target="_blank" rel="noopener noreferrer"
                        className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-foreground px-3 text-[10px] font-bold text-background">
                        <FileText className="h-3 w-3" /> Open File
                      </a>
                    ) : null}
                    {modal.linkUrl ? (
                      <a href={modal.linkUrl} target="_blank" rel="noopener noreferrer"
                        className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-foreground/15 px-3 text-[10px] font-bold">
                        <ExternalLink className="h-3 w-3" /> Open Link
                      </a>
                    ) : null}
                  </div>
                </div>
              ) : null}
              {modal.description ? (
                <div className="border-b border-foreground/5 px-4 py-3 sm:px-5">
                  <p className="mb-1 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Description</p>
                  <p className="text-xs leading-relaxed">{modal.description}</p>
                </div>
              ) : null}

              <CommentsSection resourceId={modal.resourceId} />
            </div>
          </div>
        </div>
      ) : null}
    </>
  );

  if (isAdminEmbed) {
    return (
      <AdminEmbedLayout
        title="Subject Resources"
        subtitle={subtitle}
        backUrl={props.backUrl}
        badge={props.currentStudent?.group || "Resources"}
      >
        {pageContent}
      </AdminEmbedLayout>
    );
  }

  return (
    <TelegramLayout
      topbar={
        <Topbar
          backUrl={props.backUrl}
          title="Subject Resources"
          subtitle={subtitle}
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
      {pageContent}
    </TelegramLayout>
  );
}
