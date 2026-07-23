import type { HrAnalyticsDashboard } from "@/features/recruitment/model";

export type RecruitmentFunnelStage = {
  key: string;
  label: string;
  value: number;
  conversion: number | null;
};

function formatCount(value: number) {
  return new Intl.NumberFormat("en").format(Number(value) || 0);
}

export function RecruitmentFunnel({
  stages,
  scope,
}: {
  stages: RecruitmentFunnelStage[];
  scope: HrAnalyticsDashboard["cohort_scope"];
}) {
  const viewWidth = 760;
  const viewHeight = 260;
  const centerY = viewHeight / 2;
  const horizontalInset = 12;
  const availableWidth = viewWidth - horizontalInset * 2;
  const minimumSegmentWidth = 118;
  const distributableWidth = Math.max(
    0,
    availableWidth - minimumSegmentWidth * stages.length,
  );
  const widthWeights = stages.map((stage) =>
    Math.sqrt(Math.max(0, stage.value) + 1),
  );
  const totalWidthWeight =
    widthWeights.reduce((total, weight) => total + weight, 0) || 1;
  const leadingValue = Math.max(0, stages[0]?.value || 0);
  const heightReference = Math.max(1, leadingValue);
  const minimumSegmentHeight = 126;
  const maximumSegmentHeight = 208;
  let previousHeight = maximumSegmentHeight;
  const stageHeights = stages.map((stage, index) => {
    const valueRatio = Math.min(
      1,
      Math.max(0, stage.value) / heightReference,
    );
    const valueHeight =
      minimumSegmentHeight +
      (maximumSegmentHeight - minimumSegmentHeight) *
        Math.sqrt(valueRatio);
    const height =
      index === 0 ? valueHeight : Math.min(previousHeight, valueHeight);
    previousHeight = height;
    return height;
  });
  let currentX = horizontalInset;
  const segments = stages.map((stage, index) => {
    const width =
      minimumSegmentWidth +
      distributableWidth * (widthWeights[index] / totalWidthWeight);
    const left = currentX;
    const right =
      index === stages.length - 1 ? viewWidth - horizontalInset : left + width;
    const leftHeight = stageHeights[index] || minimumSegmentHeight;
    const rightHeight = stageHeights[index + 1] || leftHeight;
    currentX = right;
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
  const accessibilityLabel = `Application cohort funnel: ${stages
    .map(
      (stage) =>
        `${stage.label}, ${stage.value} candidates${
          stage.conversion === null
            ? ", entry stage"
            : `, ${stage.conversion}% from prior stage`
        }`,
    )
    .join("; ")}.`;

  return (
    <div className="p-3">
      <p className="mb-2 text-xs leading-5 text-muted-foreground">
        Tracks valid candidates who applied during the selected month. Each
        stage is cumulative, so a candidate is included in every stage they
        reached.
      </p>
      <svg
        role="img"
        aria-label={accessibilityLabel}
        viewBox={`0 0 ${viewWidth} ${viewHeight}`}
        preserveAspectRatio="xMidYMid meet"
        className="hidden max-h-[16.25rem] w-full md:block"
      >
        <title>{accessibilityLabel}</title>
        {segments.map((segment) => (
          <polygon
            key={segment.key}
            points={segment.points}
            fill="hsl(var(--primary) / 0.10)"
            stroke="hsl(var(--primary) / 0.20)"
            strokeWidth="2"
            strokeLinejoin="round"
          />
        ))}
        {segments.slice(0, -1).map((segment) => (
          <line
            key={`${segment.key}-separator`}
            x1={segment.right}
            x2={segment.right}
            y1={centerY - segment.rightHeight / 2}
            y2={centerY + segment.rightHeight / 2}
            stroke="hsl(var(--card))"
            strokeWidth="5"
          />
        ))}
        {segments.map((segment) => {
          const conversionLabel =
            segment.conversion === null
              ? "Entry stage"
              : `${segment.conversion}% from prior`;
          const badgeWidth = segment.conversion === null ? 72 : 96;
          const labelWords = segment.label.toUpperCase().split(" ");
          const labelLines =
            segment.label.length > 12 && labelWords.length > 1
              ? [
                  labelWords.slice(0, Math.ceil(labelWords.length / 2)).join(" "),
                  labelWords.slice(Math.ceil(labelWords.length / 2)).join(" "),
                ]
              : [labelWords.join(" ")];
          return (
            <g key={`${segment.key}-content`}>
              <text
                x={segment.centerX}
                y={centerY - (labelLines.length > 1 ? 43 : 34)}
                textAnchor="middle"
                fill="hsl(var(--muted-foreground))"
                fontSize="13"
                fontWeight="700"
                letterSpacing="0.4"
              >
                {labelLines.map((line, lineIndex) => (
                  <tspan
                    key={line}
                    x={segment.centerX}
                    dy={lineIndex ? 15 : 0}
                  >
                    {line}
                  </tspan>
                ))}
              </text>
              <text
                x={segment.centerX}
                y={centerY + 11}
                textAnchor="middle"
                fill="hsl(var(--primary))"
                fontSize="32"
                fontWeight="700"
              >
                {formatCount(segment.value)}
              </text>
              <rect
                x={segment.centerX - badgeWidth / 2}
                y={centerY + 25}
                width={badgeWidth}
                height="24"
                rx="12"
                fill="hsl(var(--card))"
                stroke="hsl(var(--primary) / 0.20)"
              />
              <text
                x={segment.centerX}
                y={centerY + 41}
                textAnchor="middle"
                fill="hsl(var(--muted-foreground))"
                fontSize="10"
                fontWeight="600"
              >
                {conversionLabel}
              </text>
            </g>
          );
        })}
      </svg>

      <ol className="space-y-0 md:hidden" aria-label={accessibilityLabel}>
        {stages.map((stage, index) => (
          <li key={stage.key}>
            <div className="grid min-h-16 grid-cols-[minmax(0,1fr)_auto] items-center gap-3 rounded-lg border border-primary/20 bg-primary/10 px-3 py-2.5">
              <div className="min-w-0">
                <p className="text-[0.6875rem] font-bold uppercase leading-4 tracking-wide text-muted-foreground">
                  {stage.label}
                </p>
                <p className="mt-0.5 text-[0.625rem] font-semibold text-muted-foreground">
                  {stage.conversion === null
                    ? "Entry stage"
                    : `${stage.conversion}% from prior`}
                </p>
              </div>
              <strong className="text-2xl font-bold text-primary tabular-nums">
                {formatCount(stage.value)}
              </strong>
            </div>
            {index < stages.length - 1 ? (
              <div
                className="mx-auto h-3 w-px bg-primary/25"
                aria-hidden="true"
              />
            ) : null}
          </li>
        ))}
      </ol>

      {scope.excluded_trash_candidates > 0 ? (
        <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold leading-5 text-amber-900 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-100">
          {formatCount(scope.included_candidates)} of{" "}
          {formatCount(scope.applications_received)} applications are included
          in this cohort. {formatCount(scope.excluded_trash_candidates)}{" "}
          candidates currently in Trash are excluded.
        </p>
      ) : null}
    </div>
  );
}
