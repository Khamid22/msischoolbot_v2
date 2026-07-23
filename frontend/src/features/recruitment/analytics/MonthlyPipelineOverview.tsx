import type {
  HrAnalyticsDashboard,
  PipelineStageColorToken,
} from "@/features/recruitment/model";

const stageTones: Record<
  PipelineStageColorToken,
  { card: string; marker: string; value: string }
> = {
  neutral: {
    card: "border-slate-300 bg-slate-50 dark:border-slate-700 dark:bg-slate-900/55",
    marker: "bg-slate-500",
    value: "text-slate-800 dark:text-slate-100",
  },
  blue: {
    card: "border-blue-200 bg-blue-50/70 dark:border-blue-800 dark:bg-blue-950/25",
    marker: "bg-blue-500",
    value: "text-blue-700 dark:text-blue-200",
  },
  cyan: {
    card: "border-cyan-200 bg-cyan-50/70 dark:border-cyan-800 dark:bg-cyan-950/25",
    marker: "bg-cyan-500",
    value: "text-cyan-700 dark:text-cyan-200",
  },
  violet: {
    card: "border-violet-200 bg-violet-50/70 dark:border-violet-800 dark:bg-violet-950/25",
    marker: "bg-violet-500",
    value: "text-violet-700 dark:text-violet-200",
  },
  green: {
    card: "border-emerald-200 bg-emerald-50/70 dark:border-emerald-800 dark:bg-emerald-950/25",
    marker: "bg-emerald-500",
    value: "text-emerald-700 dark:text-emerald-200",
  },
  amber: {
    card: "border-amber-200 bg-amber-50/70 dark:border-amber-800 dark:bg-amber-950/25",
    marker: "bg-amber-500",
    value: "text-amber-700 dark:text-amber-200",
  },
  orange: {
    card: "border-orange-200 bg-orange-50/70 dark:border-orange-800 dark:bg-orange-950/25",
    marker: "bg-orange-500",
    value: "text-orange-700 dark:text-orange-200",
  },
  rose: {
    card: "border-rose-200 bg-rose-50/70 dark:border-rose-800 dark:bg-rose-950/25",
    marker: "bg-rose-500",
    value: "text-rose-700 dark:text-rose-200",
  },
};
const responsiveGridStyle = {
  gridTemplateColumns:
    "repeat(auto-fit, minmax(min(100%, 9rem), 1fr))",
};

function formatCount(value: number) {
  return new Intl.NumberFormat("en").format(Number(value) || 0);
}

export function MonthlyPipelineOverview({
  stages,
}: {
  stages: HrAnalyticsDashboard["monthly_pipeline"];
}) {
  const total = stages.reduce(
    (sum, stage) => sum + Number(stage.candidates || 0),
    0,
  );

  return (
    <div className="p-3 sm:p-4">
      <p className="text-xs leading-5 text-muted-foreground">
        Current pipeline columns for candidates who applied during the selected
        month. Each active candidate appears in one column; rejected, withdrawn,
        and other terminal outcomes are excluded.
      </p>

      <ol
        className="mt-3 grid gap-2"
        style={responsiveGridStyle}
        aria-label="Current candidates by pipeline column"
      >
        {stages.map((stage, index) => {
          const tone = stageTones[stage.color_token] || stageTones.neutral;
          return (
            <li
              key={stage.stage}
              className={`min-w-0 rounded-lg border p-3 ${tone.card}`}
            >
              <div className="flex min-h-9 items-start gap-2">
                <span
                  className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${tone.marker}`}
                  aria-hidden="true"
                />
                <div className="min-w-0">
                  <p className="text-[0.625rem] font-bold uppercase tracking-wide text-muted-foreground">
                    Column {index + 1}
                  </p>
                  <p className="mt-0.5 break-words text-xs font-bold leading-4 text-foreground">
                    {stage.stage_label}
                  </p>
                </div>
              </div>
              <p
                className={`mt-3 text-3xl font-bold tabular-nums ${tone.value}`}
              >
                {formatCount(stage.candidates)}
              </p>
              <p className="mt-0.5 text-[0.625rem] font-semibold text-muted-foreground">
                current candidates
              </p>
            </li>
          );
        })}
      </ol>

      <p className="mt-3 text-right text-xs font-semibold text-muted-foreground">
        Active pipeline candidates:{" "}
        <strong className="text-foreground tabular-nums">
          {formatCount(total)}
        </strong>
      </p>
    </div>
  );
}
