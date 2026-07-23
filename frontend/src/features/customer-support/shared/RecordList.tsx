import { Loader2, Plus, Search } from "lucide-react";
import type { RefObject } from "react";
import type { SupportRecordKind, SupportRecordSummary } from "@/features/customer-support/model";
import { RecordListItem } from "@/features/customer-support/shared/RecordListItem";
import { secondaryButton } from "@/features/customer-support/shared/ui";
import { EmptyState } from "@/shared/ui/EmptyState";

export function RecordList({
  kind,
  items,
  selectedId,
  loading,
  loadingMore,
  hasMore,
  allRecordsLoaded,
  fixedSchoolLabel,
  scrollRef,
  onSelect,
  onLoadMore,
}: {
  kind: SupportRecordKind;
  items: SupportRecordSummary[];
  selectedId: number | null;
  loading: boolean;
  loadingMore: boolean;
  hasMore: boolean;
  allRecordsLoaded: boolean;
  fixedSchoolLabel?: string;
  scrollRef: RefObject<HTMLDivElement>;
  onSelect: (item: SupportRecordSummary) => void;
  onLoadMore: () => void;
}) {
  const title = kind === "student" ? "Students" : "Parents";

  return (
    <section
      className={`${selectedId ? "hidden lg:flex" : "flex"} min-h-[28rem] min-w-0 flex-col overflow-hidden rounded-lg border border-border bg-card shadow-card lg:max-h-[calc(100dvh-14rem)]`}
      aria-label={`${title} search results`}
    >
      <header className="flex min-h-14 items-center justify-between border-b border-border px-4 py-3">
        <div>
          <h2 className="text-sm font-black">{title}</h2>
          <p className="text-xs font-semibold text-muted-foreground" aria-live="polite">
            {loading
              ? "Searching…"
              : allRecordsLoaded
                ? `${items.length} ${fixedSchoolLabel ? `${fixedSchoolLabel} ` : ""}${items.length === 1 ? kind : `${kind}s`}`
                : `${items.length} loaded`}
          </p>
        </div>
        {loading ? <Loader2 className="h-4 w-4 animate-spin text-primary motion-reduce:animate-none" aria-hidden="true" /> : null}
      </header>
      <div ref={scrollRef} className="miniapp-scroll min-h-0 flex-1 overflow-y-auto">
        {loading && !items.length ? (
          <div className="space-y-px" role="status">
            <span className="sr-only">Loading search results</span>
            {[1, 2, 3, 4].map((item) => (
              <div key={item} className="h-24 animate-pulse border-b border-border bg-muted motion-reduce:animate-none" />
            ))}
          </div>
        ) : items.length ? (
          items.map((item) => (
            <RecordListItem
              key={item.id}
              item={item}
              selected={selectedId === item.id}
              onSelect={() => onSelect(item)}
            />
          ))
        ) : (
          <EmptyState
            title={`No matching ${title.toLowerCase()}`}
            detail="Try another name, contact, school, or status."
            icon={<Search className="h-5 w-5" />}
            className="m-4"
          />
        )}
      </div>
      {hasMore ? (
        <footer className="border-t border-border p-3">
          <button type="button" onClick={onLoadMore} disabled={loadingMore} className={`${secondaryButton} w-full`}>
            {loadingMore ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" /> : <Plus className="h-4 w-4" />}
            Load more
          </button>
        </footer>
      ) : null}
    </section>
  );
}
