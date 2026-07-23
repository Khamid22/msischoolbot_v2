import type {
  HrAnalyticsDashboard,
  PipelineStageColorToken,
} from "@/features/recruitment/model";

type StageTone = {
  segment: string;
  number: string;
  mobile: string;
};

const stageTones: Record<PipelineStageColorToken, StageTone> = {
  neutral: {
    segment:
      "fill-slate-100 stroke-slate-300 dark:fill-slate-900/70 dark:stroke-slate-700",
    number: "fill-slate-800 dark:fill-slate-100",
    mobile:
      "border-slate-300 bg-slate-100 text-slate-800 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100",
  },
  blue: {
    segment:
      "fill-blue-50 stroke-blue-200 dark:fill-blue-950/60 dark:stroke-blue-800",
    number: "fill-blue-700 dark:fill-blue-200",
    mobile:
      "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-200",
  },
  cyan: {
    segment:
      "fill-cyan-50 stroke-cyan-200 dark:fill-cyan-950/60 dark:stroke-cyan-800",
    number: "fill-cyan-700 dark:fill-cyan-200",
    mobile:
      "border-cyan-200 bg-cyan-50 text-cyan-700 dark:border-cyan-800 dark:bg-cyan-950 dark:text-cyan-200",
  },
  violet: {
    segment:
      "fill-violet-50 stroke-violet-200 dark:fill-violet-950/60 dark:stroke-violet-800",
    number: "fill-violet-700 dark:fill-violet-200",
    mobile:
      "border-violet-200 bg-violet-50 text-violet-700 dark:border-violet-800 dark:bg-violet-950 dark:text-violet-200",
  },
  green: {
    segment:
      "fill-emerald-50 stroke-emerald-200 dark:fill-emerald-950/60 dark:stroke-emerald-800",
    number: "fill-emerald-700 dark:fill-emerald-200",
    mobile:
      "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
  },
  amber: {
    segment:
      "fill-amber-50 stroke-amber-200 dark:fill-amber-950/60 dark:stroke-amber-800",
    number: "fill-amber-700 dark:fill-amber-200",
    mobile:
      "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200",
  },
  orange: {
    segment:
      "fill-orange-50 stroke-orange-200 dark:fill-orange-950/60 dark:stroke-orange-800",
    number: "fill-orange-700 dark:fill-orange-200",
    mobile:
      "border-orange-200 bg-orange-50 text-orange-700 dark:border-orange-800 dark:bg-orange-950 dark:text-orange-200",
  },
  rose: {
    segment:
      "fill-rose-50 stroke-rose-200 dark:fill-rose-950/60 dark:stroke-rose-800",
    number: "fill-rose-700 dark:fill-rose-200",
    mobile:
      "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-200",
  },
};

function formatCount(value: number) {
  return new Intl.NumberFormat("en").format(Number(value) || 0);
}

function splitLabel(label: string) {
  const words = label.trim().toUpperCase().split(/\s+/);
  if (words.length < 2 || label.length <= 12) return [words.join(" ")];
  const splitAt = Math.ceil(words.length / 2);
  return [
    words.slice(0, splitAt).join(" "),
    words.slice(splitAt).join(" "),
  ];
}

export function MonthlyPipelineOverview({
  stages,
}: {
  stages: HrAnalyticsDashboard["monthly_pipeline"];
}) {
  const viewWidth = 760;
  const viewHeight = 260;
  const horizontalInset = 14;
  const centerY = viewHeight / 2;
  const maximumHeight = 198;
  const minimumHeight = 112;
  const availableWidth = viewWidth - horizontalInset * 2;
  const segmentWidth = availableWidth / Math.max(stages.length, 1);
  const heightStep =
    (maximumHeight - minimumHeight) / Math.max(stages.length, 1);
  const boundaryHeights = Array.from(
    { length: stages.length + 1 },
    (_, index) => maximumHeight - heightStep * index,
  );
  const segments = stages.map((stage, index) => {
    const left = horizontalInset + segmentWidth * index;
    const right =
      index === stages.length - 1
        ? viewWidth - horizontalInset
        : horizontalInset + segmentWidth * (index + 1);
    const leftHeight = boundaryHeights[index];
    const rightHeight = boundaryHeights[index + 1];
    return {
      ...stage,
      left,
      right,
      leftHeight,
      rightHeight,
      centerX: (left + right) / 2,
      points: [
        `${left},${centerY - leftHeight / 2}`,
        `${right},${centerY - rightHeight / 2}`,
        `${right},${centerY + rightHeight / 2}`,
        `${left},${centerY + leftHeight / 2}`,
      ].join(" "),
    };
  });
  const total = stages.reduce(
    (sum, stage) => sum + Number(stage.candidates || 0),
    0,
  );
  const accessibilityLabel = `Current pipeline columns: ${stages
    .map(
      (stage) =>
        `${stage.stage_label}, ${stage.candidates} current candidates`,
    )
    .join("; ")}.`;

  return (
    <div className="flex min-h-[20rem] flex-col items-center justify-center px-3 py-4 sm:px-4">
      <p className="max-w-2xl text-center text-xs leading-5 text-muted-foreground">
        Current column counts for candidates who applied during the selected
        month. Each active candidate appears once; terminal outcomes are
        excluded.
      </p>

      {stages.length ? (
        <>
          <svg
            role="img"
            aria-label={accessibilityLabel}
            viewBox={`0 0 ${viewWidth} ${viewHeight}`}
            preserveAspectRatio="xMidYMid meet"
            className="mx-auto mt-2 hidden max-h-[16.25rem] w-full max-w-[47.5rem] md:block"
          >
            <title>{accessibilityLabel}</title>
            {segments.map((segment) => {
              const tone =
                stageTones[segment.color_token] || stageTones.neutral;
              return (
                <polygon
                  key={segment.stage}
                  points={segment.points}
                  className={tone.segment}
                  strokeWidth="2"
                  strokeLinejoin="round"
                />
              );
            })}
            {segments.slice(0, -1).map((segment) => (
              <line
                key={`${segment.stage}-separator`}
                x1={segment.right}
                x2={segment.right}
                y1={centerY - segment.rightHeight / 2}
                y2={centerY + segment.rightHeight / 2}
                stroke="hsl(var(--card))"
                strokeWidth="5"
              />
            ))}
            {segments.map((segment) => {
              const tone =
                stageTones[segment.color_token] || stageTones.neutral;
              const labelLines = splitLabel(segment.stage_label);
              return (
                <g key={`${segment.stage}-content`}>
                  <text
                    x={segment.centerX}
                    y={centerY - (labelLines.length > 1 ? 42 : 34)}
                    textAnchor="middle"
                    fill="hsl(var(--muted-foreground))"
                    fontSize="11"
                    fontWeight="700"
                    letterSpacing="0.3"
                  >
                    {labelLines.map((line, lineIndex) => (
                      <tspan
                        key={line}
                        x={segment.centerX}
                        dy={lineIndex ? 14 : 0}
                      >
                        {line}
                      </tspan>
                    ))}
                  </text>
                  <text
                    x={segment.centerX}
                    y={centerY + 14}
                    textAnchor="middle"
                    className={tone.number}
                    fontSize="31"
                    fontWeight="750"
                  >
                    {formatCount(segment.candidates)}
                  </text>
                  <rect
                    x={segment.centerX - 30}
                    y={centerY + 29}
                    width="60"
                    height="22"
                    rx="11"
                    fill="hsl(var(--card))"
                    stroke="hsl(var(--border))"
                  />
                  <text
                    x={segment.centerX}
                    y={centerY + 44}
                    textAnchor="middle"
                    fill="hsl(var(--muted-foreground))"
                    fontSize="9"
                    fontWeight="700"
                    letterSpacing="0.4"
                  >
                    CURRENT
                  </text>
                </g>
              );
            })}
          </svg>

          <ol
            className="mt-4 flex w-full max-w-md flex-col items-center gap-1 md:hidden"
            aria-label={accessibilityLabel}
          >
            {stages.map((stage, index) => {
              const tone =
                stageTones[stage.color_token] || stageTones.neutral;
              const width =
                100 -
                (index / Math.max(stages.length - 1, 1)) * 34;
              return (
                <li
                  key={stage.stage}
                  className={`flex min-h-16 items-center justify-between gap-3 border px-7 py-2.5 ${tone.mobile}`}
                  style={{
                    width: `${width}%`,
                    clipPath:
                      "polygon(4% 0, 96% 0, 92% 100%, 8% 100%)",
                  }}
                >
                  <span className="min-w-0 break-words text-xs font-bold uppercase leading-4">
                    {stage.stage_label}
                  </span>
                  <strong className="shrink-0 text-2xl font-bold tabular-nums">
                    {formatCount(stage.candidates)}
                  </strong>
                </li>
              );
            })}
          </ol>
        </>
      ) : (
        <p className="mt-6 rounded-lg border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
          No active pipeline columns are available.
        </p>
      )}

      <p className="mt-2 text-center text-xs font-semibold text-muted-foreground">
        Active pipeline candidates:{" "}
        <strong className="text-foreground tabular-nums">
          {formatCount(total)}
        </strong>
      </p>
    </div>
  );
}
