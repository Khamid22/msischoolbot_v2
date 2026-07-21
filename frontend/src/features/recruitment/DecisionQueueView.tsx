import { ArrowRight, ClipboardCheck, ShieldCheck, UserRound } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { recruitmentRequest } from "@/features/recruitment/api";
import { dateLabel, humanize, stageLabels, type RecruitmentCandidate } from "@/features/recruitment/model";
import {
  RECRUITMENT_API,
  EmptyLine,
  PageState,
  rememberRecruitmentReturn,
  replaceUrlParams,
  restoreRecruitmentReturn,
} from "@/features/recruitment/ui";
import { Pagination } from "@/shared/ui/Pagination";
import { StatusBadge } from "@/shared/ui/StatusBadge";

type DecisionQueueData = {
  items: RecruitmentCandidate[];
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
};

export function DecisionQueueView({ basePath }: { basePath: string }) {
  const [page, setPage] = useState(() => {
    const requested = Number(new URLSearchParams(window.location.search).get("page") || 1);
    return Number.isFinite(requested) && requested > 0 ? Math.floor(requested) : 1;
  });
  const showUpdatedNotice = new URLSearchParams(window.location.search).get("updated") === "1";
  const queue = useQuery({
    queryKey: ["recruitment", "decision-queue", page],
    queryFn: () => recruitmentRequest<DecisionQueueData>(`${RECRUITMENT_API}/decision-queue?page=${page}&per_page=25`),
  });

  useEffect(() => {
    replaceUrlParams({ page });
  }, [page]);

  useEffect(() => {
    if (queue.data) restoreRecruitmentReturn("decisions");
  }, [queue.data]);

  const openCandidate = (candidateId: number) =>
    `${basePath}/candidates/${candidateId}?tab=hiring&origin=decisions`;

  if (queue.isLoading) return <PageState>Loading decision queue…</PageState>;
  if (queue.error || !queue.data) return <PageState tone="error">Unable to load the decision queue.</PageState>;

  return (
    <div className="space-y-2">
      {showUpdatedNotice ? (
        <div role="status" className="rounded-xl border border-success/25 bg-success/10 px-3 py-3 text-sm font-semibold text-success">
          Recruitment decision recorded. The queue has been refreshed.
        </div>
      ) : null}

      <section className="rounded-xl border border-border bg-card p-3" aria-labelledby="decision-queue-heading">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 id="decision-queue-heading" className="flex items-center gap-2 text-sm font-semibold">
              <ShieldCheck className="h-4 w-4 text-primary" /> Academic decisions
            </h2>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              Hiring requests appear first, followed by candidates assigned for evaluation.
            </p>
          </div>
          <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-semibold tabular-nums text-muted-foreground">
            {queue.data.total} open
          </span>
        </div>
      </section>

      {queue.data.items.length ? (
        <section className="grid gap-2 lg:grid-cols-2" aria-label="Candidates awaiting Academic Director action">
          {queue.data.items.map((candidate) => {
            const approval = candidate.actionable_approval;
            return (
              <article key={candidate.id} className="rounded-xl border border-border bg-card p-3 shadow-sm">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <h3 className="truncate text-sm font-semibold text-foreground">{candidate.full_name}</h3>
                    <p className="mt-0.5 truncate text-xs text-muted-foreground">
                      {candidate.applied_position || candidate.subject || "Position not set"}
                    </p>
                  </div>
                  <StatusBadge status={candidate.status}>{candidate.status_label || stageLabels[candidate.status] || humanize(candidate.status)}</StatusBadge>
                </div>

                <div className="mt-3 rounded-lg bg-muted/50 px-3 py-1.5">
                  {approval ? (
                    <>
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="flex items-center gap-1.5 text-[13px] font-semibold">
                          <ClipboardCheck className="h-4 w-4 text-primary" />
                          {stageLabels[approval.requested_outcome] || humanize(approval.requested_outcome)}
                        </span>
                        <StatusBadge status={approval.status} />
                      </div>
                      <p className="mt-1.5 line-clamp-2 text-xs leading-5 text-muted-foreground">
                        {approval.request_note || "No request note provided."}
                      </p>
                      <p className="mt-1 text-[11px] text-muted-foreground">Requested {dateLabel(approval.created_at)}</p>
                    </>
                  ) : (
                    <div className="flex items-center gap-2 text-[13px] font-semibold">
                      <UserRound className="h-4 w-4 text-primary" /> Evaluation assigned
                    </div>
                  )}
                </div>

                <a
                  href={openCandidate(candidate.id)}
                  onClick={() => rememberRecruitmentReturn("decisions")}
                  className="mt-3 inline-flex min-h-9 w-full items-center justify-center gap-2 rounded-lg bg-primary px-3 text-[13px] font-semibold text-primary-foreground transition-colors hover:brightness-105 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 motion-reduce:transition-none"
                >
                  Review candidate <ArrowRight className="h-4 w-4" />
                </a>
              </article>
            );
          })}
        </section>
      ) : (
        <EmptyLine>No candidates currently require an Academic Director decision.</EmptyLine>
      )}

      {queue.data.total_pages > 1 ? (
        <div className="rounded-xl border border-border bg-card p-3">
          <Pagination
            page={page}
            totalPages={queue.data.total_pages}
            onPageChange={(next) => {
              setPage(next);
              window.scrollTo({ top: 0, behavior: "auto" });
            }}
            label={`${queue.data.total} candidates · Page ${page} of ${queue.data.total_pages}`}
          />
        </div>
      ) : null}
    </div>
  );
}
