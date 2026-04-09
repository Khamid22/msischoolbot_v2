import { useState } from "react";
import { BookOpen, ExternalLink, FileText, Play, X } from "lucide-react";
import { ChartCard } from "@/components/ChartCard";
import { TelegramLayout, Topbar } from "@/components/TelegramLayout";

interface ResourceRow {
  id: number;
  title: string;
  description?: string;
  resource_url?: string;
  resource_file_url?: string;
  resource_file_kind?: string;
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

export default function ResourcesPage(props: ResourcesPageProps) {
  const [activeFilter, setActiveFilter] = useState("all");
  const [videoModal, setVideoModal] = useState<{ title: string; src: string } | null>(null);
  const groupedResources = Array.isArray(props.groupedResources) ? props.groupedResources : [];
  const totalCount = groupedResources.reduce((sum, group) => sum + group.resources.length, 0);
  const visibleGroups =
    activeFilter === "all"
      ? groupedResources
      : groupedResources.filter((_group, index) => activeFilter === `group-${index + 1}`);

  return (
    <TelegramLayout
      topbar={
        <Topbar
          backUrl={props.backUrl}
          title="Subject Resources"
          subtitle={`${props.subjectName || "Resources"} · ${totalCount} items`}
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
      <div className="space-y-3 animate-in sm:space-y-4">
        <ChartCard
          title="Resource Library"
          subtitle="Choose a resource type"
          icon={<BookOpen className="h-4 w-4 text-info" />}
        >
          <div className="-mx-4 flex snap-x snap-mandatory gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:px-1">
            <button
              type="button"
              onClick={() => setActiveFilter("all")}
              className={`inline-flex shrink-0 snap-start items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold ${
                activeFilter === "all" ? "bg-primary text-primary-foreground shadow-neo" : "bg-surface shadow-card"
              }`}
            >
              All <span className="opacity-70">{totalCount}</span>
            </button>
            {groupedResources.map((group, index) => {
              const filterKey = `group-${index + 1}`;
              return (
                <button
                  key={filterKey}
                  type="button"
                  onClick={() => setActiveFilter(filterKey)}
                  className={`inline-flex shrink-0 snap-start items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold ${
                    activeFilter === filterKey ? "bg-primary text-primary-foreground shadow-neo" : "bg-surface shadow-card"
                  }`}
                >
                  {group.resource_type_name}
                  <span className="opacity-70">{group.resources.length}</span>
                </button>
              );
            })}
          </div>
        </ChartCard>

        {groupedResources.length ? (
          visibleGroups.map((group, index) => {
            const filterKey = activeFilter === "all" ? `visible-group-${index + 1}` : activeFilter;

            return (
              <ChartCard
                key={filterKey}
                title={group.resource_type_name}
                subtitle={`${group.resources.length} item${group.resources.length === 1 ? "" : "s"}`}
                icon={<BookOpen className="h-4 w-4 text-info" />}
              >
                <div className="divide-y divide-foreground/5 overflow-hidden rounded-xl border border-foreground/5 bg-background/40">
                  {group.resources.map((item) => {
                    const isVideo = item.resource_file_url && item.resource_file_kind === "video";
                    const hasFile = item.resource_file_url && item.resource_file_kind !== "video";
                    return (
                      <article key={item.id} className="p-3 sm:p-4">
                        <div className="flex min-w-0 flex-1 items-start gap-3">
                          <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground sm:h-10 sm:w-10">
                            {isVideo ? <Play className="h-5 w-5" /> : hasFile ? <FileText className="h-5 w-5" /> : <BookOpen className="h-5 w-5" />}
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between sm:gap-3">
                              <div className="min-w-0 flex-1">
                                <h4 className="text-sm font-bold leading-snug break-words">{item.title}</h4>
                              </div>
                              <div className="flex w-full shrink-0 flex-col gap-2 sm:w-auto sm:min-w-[140px] sm:items-end">
                                {isVideo ? (
                                  <button
                                    type="button"
                                    onClick={() => setVideoModal({ title: item.title, src: item.resource_file_url || "" })}
                                    className="inline-flex min-h-9 w-full items-center justify-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-[11px] font-bold text-primary-foreground sm:w-auto"
                                  >
                                    <Play className="h-3 w-3" />
                                    Watch Video
                                  </button>
                                ) : null}
                                {hasFile ? (
                                  <a
                                    href={item.resource_file_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex min-h-9 w-full items-center justify-center gap-1.5 rounded-lg border-2 border-foreground/10 px-3 py-2 text-[11px] font-bold hover:bg-muted sm:w-auto"
                                  >
                                    <FileText className="h-3 w-3" />
                                    Open File
                                  </a>
                                ) : null}
                                {!hasFile && !isVideo && item.resource_url ? (
                                  <a
                                    href={item.resource_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex min-h-9 w-full items-center justify-center gap-1.5 rounded-lg border-2 border-foreground/10 px-3 py-2 text-[11px] font-bold hover:bg-muted sm:w-auto"
                                  >
                                    <ExternalLink className="h-3 w-3" />
                                    Open Link
                                  </a>
                                ) : null}
                              </div>
                            </div>
                            {item.description ? (
                              <p className="mt-1 text-xs leading-5 text-muted-foreground sm:pr-2">{item.description}</p>
                            ) : null}
                            {hasFile && item.resource_url ? (
                              <div className="mt-2">
                                <a
                                  href={item.resource_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-muted-foreground hover:text-foreground"
                                >
                                  <ExternalLink className="h-3 w-3" />
                                  Open reference link
                                </a>
                              </div>
                            ) : null}
                          </div>
                        </div>
                      </article>
                    );
                  })}
                </div>
              </ChartCard>
            );
          })
        ) : (
          <ChartCard title="Resources" icon={<BookOpen className="h-4 w-4 text-info" />}>
            <p className="text-sm text-muted-foreground">No resources are available for this subject yet.</p>
          </ChartCard>
        )}
      </div>

      {videoModal ? (
        <div className="tg-fixed-fullscreen fixed inset-0 z-50 flex items-center justify-center bg-foreground/60">
          <div className="flex h-full w-full max-h-full flex-col overflow-hidden bg-surface shadow-card-hover sm:h-auto sm:max-w-3xl sm:rounded-2xl">
            <div className="flex items-center justify-between gap-3 border-b border-foreground/5 p-4">
              <h3 className="truncate font-display text-sm font-bold">{videoModal.title}</h3>
              <button
                type="button"
                onClick={() => setVideoModal(null)}
                className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div
              className="flex-1 sm:aspect-video sm:flex-none"
              style={{ backgroundColor: "var(--tg-theme-secondary-bg-color, hsl(var(--muted)))" }}
            >
              <video className="h-full w-full object-contain" controls playsInline preload="metadata" src={videoModal.src} />
            </div>
          </div>
        </div>
      ) : null}
    </TelegramLayout>
  );
}
