import { ChevronRight, ContactRound, Loader2, Plus, Search } from "lucide-react";
import type { RefObject } from "react";
import type { TeacherDirectoryItem } from "@/features/customer-support/model";
import { secondaryButton } from "@/features/customer-support/shared/ui";
import { EmptyState } from "@/shared/ui/EmptyState";
import { StatusBadge } from "@/shared/ui/StatusBadge";

export function TeacherList({
  items,
  selectedId,
  loading,
  loadingMore,
  hasMore,
  scrollRef,
  onSelect,
  onLoadMore,
}: {
  items: TeacherDirectoryItem[];
  selectedId: number | null;
  loading: boolean;
  loadingMore: boolean;
  hasMore: boolean;
  scrollRef: RefObject<HTMLDivElement>;
  onSelect: (teacher: TeacherDirectoryItem) => void;
  onLoadMore: () => void;
}) {
  return (
    <section
      className="flex min-h-[28rem] min-w-0 flex-col overflow-hidden rounded-lg border border-border bg-card shadow-card lg:max-h-[calc(100dvh-14rem)]"
      aria-label="Teacher search results"
    >
      <header className="flex min-h-14 items-center justify-between border-b border-border px-4 py-3">
        <div>
          <h2 className="text-sm font-black">Teachers</h2>
          <p className="text-xs font-semibold text-muted-foreground" aria-live="polite">
            {loading ? "Searching…" : `${items.length} loaded`}
          </p>
        </div>
        {loading ? (
          <Loader2
            className="h-4 w-4 animate-spin text-primary motion-reduce:animate-none"
            aria-hidden="true"
          />
        ) : null}
      </header>
      <div ref={scrollRef} className="miniapp-scroll min-h-0 flex-1 overflow-y-auto">
        {loading && !items.length ? (
          <div className="space-y-px" role="status">
            <span className="sr-only">Loading teachers</span>
            {[1, 2, 3, 4].map((item) => (
              <div
                key={item}
                className="h-24 animate-pulse border-b border-border bg-muted motion-reduce:animate-none"
              />
            ))}
          </div>
        ) : items.length ? (
          items.map((teacher) => (
            <button
              key={teacher.teacherId}
              type="button"
              onClick={() => onSelect(teacher)}
              aria-pressed={selectedId === teacher.teacherId}
              className={`flex min-h-[6.25rem] w-full items-start gap-3 border-b border-border px-4 py-3 text-left transition-colors duration-150 last:border-b-0 hover:bg-muted/70 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/40 motion-reduce:transition-none ${selectedId === teacher.teacherId ? "bg-primary/8" : "bg-card"}`}
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-sky-50 text-sky-700">
                <ContactRound className="h-5 w-5" aria-hidden="true" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex flex-wrap items-start justify-between gap-2">
                  <span className="break-words text-sm font-black text-foreground">
                    {teacher.fullName}
                  </span>
                  <StatusBadge
                    status={teacher.accountStatus}
                    className="shrink-0 text-[0.625rem]"
                  />
                </span>
                <span className="mt-1 block break-words text-xs font-semibold text-muted-foreground">
                  {teacher.login || teacher.phone || "No account contact"}
                </span>
                <span className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs font-bold text-muted-foreground">
                  <span>{teacher.schoolNames.join(", ") || "School not assigned"}</span>
                  <span>{teacher.subjectNames.join(", ") || "No subjects assigned"}</span>
                  <span>
                    {teacher.assignedGroupCount} {teacher.assignedGroupCount === 1 ? "group" : "groups"}
                  </span>
                </span>
              </span>
              <ChevronRight
                className="mt-2 h-4 w-4 shrink-0 text-muted-foreground"
                aria-hidden="true"
              />
            </button>
          ))
        ) : (
          <EmptyState
            title="No matching teachers"
            detail="Try another name, login, contact, school, subject, group, or status."
            icon={<Search className="h-5 w-5" />}
            className="m-4"
          />
        )}
      </div>
      {hasMore ? (
        <footer className="border-t border-border p-3">
          <button
            type="button"
            onClick={onLoadMore}
            disabled={loadingMore}
            className={`${secondaryButton} w-full`}
          >
            {loadingMore ? (
              <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" />
            ) : (
              <Plus className="h-4 w-4" />
            )}
            Load more
          </button>
        </footer>
      ) : null}
    </section>
  );
}
