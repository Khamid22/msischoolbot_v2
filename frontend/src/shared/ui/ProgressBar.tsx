interface ProgressBarProps {
  value: number;
  max?: number;
  /** Accessible name, e.g. "Academy lessons completed". */
  label?: string;
  /** Render a compact "3/12" fraction next to the bar. */
  showFraction?: boolean;
  className?: string;
  fillClassName?: string;
}

export function ProgressBar({
  value,
  max = 100,
  label,
  showFraction = false,
  className = "",
  fillClassName = "bg-progress-accent",
}: ProgressBarProps) {
  const safeMax = max > 0 ? max : 100;
  const clamped = Math.min(safeMax, Math.max(0, value));
  const pct = (clamped / safeMax) * 100;

  const track = (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={safeMax}
      aria-valuenow={clamped}
      className={`h-2 w-full overflow-hidden rounded-full bg-muted ${showFraction ? "" : className}`}
    >
      <div
        className={`${fillClassName} h-full rounded-full transition-all duration-300 ease-out motion-reduce:transition-none`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );

  if (!showFraction) return track;

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {track}
      <span className="shrink-0 text-[11px] font-bold tabular-nums text-muted-foreground">
        {clamped}/{safeMax}
      </span>
    </div>
  );
}
