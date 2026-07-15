import { Ban, Search, UserMinus } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { recruitmentRequest } from "@/features/recruitment/api";
import { dateLabel, humanize, stageLabels, type RecruitmentCandidate } from "@/features/recruitment/model";
import {
  RECRUITMENT_API,
  EmptyLine,
  PageState,
  fieldClass,
  queryError,
  rememberRecruitmentReturn,
  replaceUrlParams,
  restoreRecruitmentReturn,
} from "@/features/recruitment/ui";
import { Pagination } from "@/shared/ui/Pagination";
import { StatusBadge } from "@/shared/ui/StatusBadge";

type RejectedData = {
  items: RecruitmentCandidate[];
  page: number;
  total: number;
  total_pages: number;
};

type OutcomeTab = "rejected" | "candidate_withdrew";

export function RejectedCandidatesView({ basePath }: { basePath: string }) {
  const initial = new URLSearchParams(window.location.search);
  const [tab, setTab] = useState<OutcomeTab>(initial.get("tab") === "candidate_withdrew" ? "candidate_withdrew" : "rejected");
  const [page, setPage] = useState(() => Math.max(1, Number(initial.get("page") || 1)));
  const [search, setSearch] = useState(initial.get("search") || "");
  const params = new URLSearchParams({ page: String(page), per_page: "25", stage: tab });
  if (search) params.set("search", search);
  const candidates = useQuery({
    queryKey: ["recruitment", "outcomes", tab, page, search],
    queryFn: () => recruitmentRequest<RejectedData>(`${RECRUITMENT_API}/candidates?${params}`),
  });

  useEffect(() => {
    replaceUrlParams({ tab, page, search }, ["stage", "per_page"]);
  }, [page, search, tab]);
  useEffect(() => {
    if (candidates.data) restoreRecruitmentReturn("rejected");
  }, [candidates.data]);

  const switchTab = (next: OutcomeTab) => {
    setTab(next);
    setPage(1);
  };
  const returnQuery = encodeURIComponent(`?tab=${tab}&page=${page}${search ? `&search=${encodeURIComponent(search)}` : ""}`);

  return (
    <div className="space-y-3">
      <section className="rounded-xl border border-border bg-card p-3">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div role="tablist" aria-label="Closed recruitment outcomes" className="inline-flex rounded-lg border border-border bg-muted/40 p-1">
            <button type="button" role="tab" aria-selected={tab === "rejected"} onClick={() => switchTab("rejected")} className={`min-h-11 rounded-md px-3 text-sm font-semibold ${tab === "rejected" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}>Rejected</button>
            <button type="button" role="tab" aria-selected={tab === "candidate_withdrew"} onClick={() => switchTab("candidate_withdrew")} className={`min-h-11 rounded-md px-3 text-sm font-semibold ${tab === "candidate_withdrew" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}>Withdrawn</button>
          </div>
          <label className="block w-full text-xs font-semibold text-muted-foreground md:max-w-sm">
            Search
            <span className="relative mt-1 block">
              <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4" />
              <input className={`${fieldClass} pl-9`} value={search} onChange={(event) => { setPage(1); setSearch(event.target.value); }} placeholder="Candidate name" />
            </span>
          </label>
        </div>
      </section>

      {candidates.isLoading ? <PageState>Loading closed candidates…</PageState> : null}
      {candidates.error ? <PageState tone="error">{queryError(candidates.error)}</PageState> : null}
      {candidates.data ? (
        <section className="overflow-hidden rounded-xl border border-border bg-card">
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full min-w-[760px] text-left text-[13px]">
              <thead className="bg-muted/60 text-[11px] uppercase tracking-wide text-muted-foreground"><tr><th className="px-3 py-2.5">Candidate</th><th className="px-3 py-2.5">Failed / left at</th><th className="px-3 py-2.5">Reason</th><th className="px-3 py-2.5">Recorded</th></tr></thead>
              <tbody className="divide-y divide-border">{candidates.data.items.map((candidate) => (
                <tr key={candidate.id} className="hover:bg-muted/30">
                  <td className="px-3 py-2.5"><a href={`${basePath}/candidates/${candidate.id}?tab=hiring&origin=rejected&return=${returnQuery}`} onClick={() => rememberRecruitmentReturn("rejected")} className="inline-flex min-h-11 items-center font-semibold hover:text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30">{candidate.full_name}</a><p className="text-xs text-muted-foreground">{candidate.applied_position || candidate.subject || "Position not set"}</p></td>
                  <td className="px-3 py-2.5"><StatusBadge status={candidate.decision_origin_stage || "new_candidate"}>{stageLabels[candidate.decision_origin_stage || ""] || humanize(candidate.decision_origin_stage || "Unknown")}</StatusBadge></td>
                  <td className="max-w-md px-3 py-2.5"><p className="line-clamp-2">{candidate.rejection_reason ? humanize(candidate.rejection_reason) : candidate.decision_reason_detail || "No reason recorded"}</p>{candidate.rejection_reason && candidate.decision_reason_detail ? <p className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">{candidate.decision_reason_detail}</p> : null}</td>
                  <td className="px-3 py-2.5 text-muted-foreground">{dateLabel(candidate.final_decision_at || candidate.stage_changed_at)}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
          <div className="divide-y divide-border md:hidden">{candidates.data.items.map((candidate) => (
            <a key={candidate.id} href={`${basePath}/candidates/${candidate.id}?tab=hiring&origin=rejected&return=${returnQuery}`} onClick={() => rememberRecruitmentReturn("rejected")} className="block p-3 hover:bg-muted/30">
              <div className="flex items-start justify-between gap-2"><span className="text-sm font-semibold">{candidate.full_name}</span><StatusBadge status={tab}>{tab === "rejected" ? "Rejected" : "Withdrawn"}</StatusBadge></div>
              <p className="mt-1 text-xs text-muted-foreground">From {stageLabels[candidate.decision_origin_stage || ""] || humanize(candidate.decision_origin_stage || "Unknown stage")}</p>
              <p className="mt-1 line-clamp-2 text-[13px]">{candidate.rejection_reason ? humanize(candidate.rejection_reason) : candidate.decision_reason_detail || "No reason recorded"}</p>
            </a>
          ))}</div>
          {!candidates.data.items.length ? <div className="p-4"><EmptyLine><span className="inline-flex items-center gap-2">{tab === "rejected" ? <Ban className="h-4 w-4" /> : <UserMinus className="h-4 w-4" />}{tab === "rejected" ? "No rejected candidates." : "No withdrawn candidates."}</span></EmptyLine></div> : null}
          <div className="p-3"><Pagination page={page} totalPages={candidates.data.total_pages} onPageChange={setPage} label={`${candidates.data.total} candidates · Page ${page} of ${candidates.data.total_pages}`} /></div>
        </section>
      ) : null}
    </div>
  );
}
