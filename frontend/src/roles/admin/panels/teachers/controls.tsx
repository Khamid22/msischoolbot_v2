

export function StageButton({
  label,
  tone = "primary",
  disabled,
  onClick,
}: {
  label: string;
  tone?: "primary" | "muted" | "danger";
  disabled: boolean;
  onClick: () => void;
}) {
  const toneClass =
    tone === "danger"
      ? "border border-destructive/20 bg-destructive/10 text-destructive hover:bg-destructive/15"
      : tone === "muted"
        ? "border border-foreground/10 bg-surface text-foreground hover:bg-muted"
        : "bg-primary text-primary-foreground hover:opacity-90";
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`min-h-8 min-w-0 rounded-lg px-3 py-1.5 text-xs font-bold leading-tight transition-opacity disabled:opacity-50 ${toneClass}`}
    >
      {label}
    </button>
  );
}

export function PaginationControls({
  page,
  totalPages,
  onPageChange,
  label,
}: {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  label?: string;
}) {
  if (totalPages <= 1) {
    return null;
  }

  return (
    <div className="flex items-center justify-between gap-2 border-t border-foreground/5 pt-2">
      <span className="text-[11px] font-semibold text-muted-foreground">
        {label || `Page ${page} of ${totalPages}`}
      </span>
      <div className="flex items-center gap-1">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onPageChange(Math.max(1, page - 1))}
          className="h-7 rounded-md border border-foreground/10 px-2 text-[11px] font-bold text-muted-foreground hover:bg-muted disabled:opacity-40"
        >
          Prev
        </button>
        <button
          type="button"
          disabled={page >= totalPages}
          onClick={() => onPageChange(Math.min(totalPages, page + 1))}
          className="h-7 rounded-md border border-foreground/10 px-2 text-[11px] font-bold text-muted-foreground hover:bg-muted disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  );
}

