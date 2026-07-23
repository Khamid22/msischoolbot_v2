import { Ban, UserMinus } from "lucide-react";

import type { HrAnalyticsDashboard } from "@/features/recruitment/model";

export type OutcomeTab = "rejected" | "candidate_withdrew";

const reasonColors = [
  "#4F6BED",
  "#F59E0B",
  "#10B981",
  "#8B5CF6",
  "#F43F5E",
  "#06B6D4",
  "#84CC16",
  "#F97316",
];

function formatCount(value: number) {
  return new Intl.NumberFormat("en").format(Number(value) || 0);
}

function ReasonDistribution({
  breakdown,
}: {
  breakdown: HrAnalyticsDashboard["total_outcome_reason_breakdown"][OutcomeTab];
}) {
  if (!breakdown.total) {
    return (
      <div className="flex min-h-36 items-center justify-center p-4">
        <p className="rounded-lg border border-dashed border-border px-4 py-6 text-center text-sm text-muted-foreground">
          No outcomes were recorded for this filter selection.
        </p>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="flex items-center gap-3">
        <div className="shrink-0">
          <p className="text-[0.6875rem] font-bold uppercase tracking-wide text-muted-foreground">
            Total
          </p>
          <p className="text-3xl font-bold tabular-nums">
            {formatCount(breakdown.total)}
          </p>
        </div>
        <div
          className="flex h-4 min-w-0 flex-1 overflow-hidden rounded-full border border-border bg-muted"
          aria-hidden="true"
        >
          {breakdown.items.map((item, index) => (
            <span
              key={item.value}
              className="h-full first:rounded-l-full last:rounded-r-full"
              style={{
                width: `${item.percentage}%`,
                backgroundColor: reasonColors[index % reasonColors.length],
              }}
            />
          ))}
        </div>
      </div>
      <ul
        className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-3"
        aria-label="Outcome reason distribution"
      >
        {breakdown.items.map((item, index) => (
          <li
            key={item.value}
            className="flex min-h-14 items-center justify-between gap-3 rounded-lg border border-border/70 bg-muted/20 px-3 py-2"
          >
            <span className="flex min-w-0 items-center gap-2">
              <span
                className="h-3 w-3 shrink-0 rounded-sm"
                style={{
                  backgroundColor: reasonColors[index % reasonColors.length],
                }}
                aria-hidden="true"
              />
              <span className="min-w-0 break-words text-xs font-semibold">
                {item.label}
              </span>
            </span>
            <span className="shrink-0 text-right">
              <strong className="block text-sm tabular-nums">
                {formatCount(item.candidates)}
              </strong>
              <span className="text-[0.625rem] font-semibold text-muted-foreground tabular-nums">
                {item.percentage}%
              </span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function CandidateOutcomes({
  outcomes,
  breakdown,
  selected,
  onSelect,
}: {
  outcomes: HrAnalyticsDashboard["total_outcomes"];
  breakdown: HrAnalyticsDashboard["total_outcome_reason_breakdown"];
  selected: OutcomeTab;
  onSelect: (outcome: OutcomeTab) => void;
}) {
  const cards = [
    {
      key: "rejected" as const,
      label: "Rejected",
      value: outcomes.rejected,
      icon: Ban,
      tone: "border-rose-200 bg-rose-50/70 dark:border-rose-800 dark:bg-rose-950/25",
      iconTone: "bg-rose-100 text-rose-700 dark:bg-rose-900/60 dark:text-rose-200",
    },
    {
      key: "candidate_withdrew" as const,
      label: "Candidate Withdrew",
      value: outcomes.candidate_withdrew,
      icon: UserMinus,
      tone: "border-amber-200 bg-amber-50/70 dark:border-amber-800 dark:bg-amber-950/25",
      iconTone: "bg-amber-100 text-amber-700 dark:bg-amber-900/60 dark:text-amber-200",
    },
  ];

  return (
    <section
      className="overflow-hidden rounded-xl border border-border bg-card shadow-sm"
      aria-labelledby="candidate-outcomes-title"
    >
      <header className="border-b border-border/70 px-4 py-3">
        <h2
          id="candidate-outcomes-title"
          className="text-sm font-bold text-foreground"
        >
          Candidate Outcomes · All time
        </h2>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">
          Outcomes are distinct current final candidate outcomes across all
          time.
        </p>
      </header>

      <div className="grid gap-2 p-3 sm:grid-cols-2 sm:p-4">
        {cards.map((card) => {
          const Icon = card.icon;
          const active = selected === card.key;
          return (
            <button
              key={card.key}
              type="button"
              aria-pressed={active}
              onClick={() => onSelect(card.key)}
              className={`flex min-h-20 items-center justify-between gap-3 rounded-lg border p-3 text-left transition-shadow focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 motion-reduce:transition-none ${card.tone} ${
                active ? "ring-2 ring-primary/25 shadow-sm" : ""
              }`}
            >
              <span className="flex min-w-0 items-center gap-3">
                <span
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${card.iconTone}`}
                  aria-hidden="true"
                >
                  <Icon className="h-4 w-4" />
                </span>
                <span className="text-xs font-bold uppercase leading-4 tracking-wide text-muted-foreground">
                  {card.label}
                </span>
              </span>
              <strong className="shrink-0 text-2xl font-bold text-foreground tabular-nums">
                {formatCount(card.value)}
              </strong>
            </button>
          );
        })}
      </div>

      <div className="border-t border-border/70">
        <div className="flex flex-wrap items-center justify-between gap-2 px-4 pt-3">
          <p className="text-xs font-bold text-foreground">
            Outcome reason distribution
          </p>
          <div
            role="tablist"
            aria-label="Candidate outcome type"
            className="inline-flex rounded-lg border border-border bg-muted/45 p-1"
          >
            {cards.map((card, index) => {
              const active = selected === card.key;
              const next = cards[index === cards.length - 1 ? 0 : index + 1].key;
              return (
                <button
                  key={card.key}
                  id={`analytics-outcome-tab-${card.key}`}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  aria-controls="analytics-outcome-panel"
                  tabIndex={active ? 0 : -1}
                  onClick={() => onSelect(card.key)}
                  onKeyDown={(event) => {
                    if (
                      event.key === "ArrowRight" ||
                      event.key === "ArrowLeft"
                    )
                      onSelect(next);
                  }}
                  className={`min-h-9 rounded-md px-3 text-xs font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 motion-reduce:transition-none ${
                    active
                      ? "bg-card text-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {card.label}
                  <span className="ml-1.5 tabular-nums">
                    {formatCount(card.value)}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
        <div
          id="analytics-outcome-panel"
          role="tabpanel"
          aria-labelledby={`analytics-outcome-tab-${selected}`}
        >
          <ReasonDistribution breakdown={breakdown[selected]} />
        </div>
      </div>
    </section>
  );
}
