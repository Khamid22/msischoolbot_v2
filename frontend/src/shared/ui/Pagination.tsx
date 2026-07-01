import { ChevronLeft, ChevronRight } from "lucide-react";

interface PaginationProps {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  label?: string;
}

export function Pagination({ page, totalPages, onPageChange, label }: PaginationProps) {
  if (totalPages <= 1) {
    return null;
  }

  const current = Math.max(1, Math.min(page, totalPages));

  return (
    <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-t border-foreground/5 px-1 pt-2">
      <span className="text-[11px] font-semibold text-muted-foreground">
        {label || `Page ${current} of ${totalPages}`}
      </span>
      <div className="flex items-center gap-1">
        <button
          type="button"
          disabled={current <= 1}
          onClick={() => onPageChange(Math.max(1, current - 1))}
          className="inline-flex h-7 items-center gap-1 rounded-md border border-foreground/10 px-2 text-[11px] font-bold text-muted-foreground hover:bg-muted disabled:opacity-40"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
          Prev
        </button>
        <span className="min-w-8 rounded-md bg-primary px-2 py-1 text-center text-[11px] font-bold text-primary-foreground">
          {current}
        </span>
        <button
          type="button"
          disabled={current >= totalPages}
          onClick={() => onPageChange(Math.min(totalPages, current + 1))}
          className="inline-flex h-7 items-center gap-1 rounded-md border border-foreground/10 px-2 text-[11px] font-bold text-muted-foreground hover:bg-muted disabled:opacity-40"
        >
          Next
          <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
