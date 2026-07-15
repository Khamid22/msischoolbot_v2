import { Search, Trash2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { recruitmentRequest } from "@/features/recruitment/api";
import { dateLabel, type RecruitmentCandidate } from "@/features/recruitment/model";
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

type TrashBinData = {
  items: RecruitmentCandidate[];
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
};

export function TrashBinView({ basePath }: { basePath: string }) {
  const initialParams = new URLSearchParams(window.location.search);
  const [page, setPage] = useState(() => {
    const requestedPage = Number(initialParams.get("page") || 1);
    return Number.isFinite(requestedPage) && requestedPage > 0 ? Math.floor(requestedPage) : 1;
  });
  const [search, setSearch] = useState(() => initialParams.get("search") || "");
  const requestParams = new URLSearchParams({
    page: String(page),
    per_page: "25",
    stage: "trash_bin",
  });
  if (search) requestParams.set("search", search);

  const candidates = useQuery({
    queryKey: ["recruitment", "trash", page, search],
    queryFn: () => recruitmentRequest<TrashBinData>(`${RECRUITMENT_API}/candidates?${requestParams}`),
  });

  useEffect(() => {
    replaceUrlParams({ page, search }, ["stage", "position", "source", "application_from", "application_to", "final_decision", "evaluator_account_id", "per_page"]);
  }, [page, search]);

  useEffect(() => {
    if (candidates.data) restoreRecruitmentReturn("trash");
  }, [candidates.data]);

  const deletedCandidates = candidates.data?.items.filter((candidate) => candidate.status === "trash_bin") || [];
  const returnParams = new URLSearchParams({ page: String(page) });
  if (search) returnParams.set("search", search);
  const returnQuery = encodeURIComponent(`?${returnParams.toString()}`);
  const candidateHref = (candidateId: number) => `${basePath}/candidates/${candidateId}?tab=overview&origin=trash&return=${returnQuery}`;

  return (
    <div className="space-y-3">
      <section className="rounded-xl border border-border bg-card p-3">
        <label className="block max-w-xl text-xs font-semibold text-muted-foreground">
          Search deleted candidates
          <span className="relative mt-1 block">
            <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4" />
            <input
              className={`${fieldClass} pl-9`}
              value={search}
              onChange={(event) => { setPage(1); setSearch(event.target.value); }}
              placeholder="Candidate name"
            />
          </span>
        </label>
      </section>

      {candidates.isLoading ? <PageState>Loading Trash Bin…</PageState> : null}
      {candidates.error ? <PageState tone="error">{queryError(candidates.error)}</PageState> : null}
      {candidates.data ? (
        <section className="overflow-hidden rounded-xl border border-border bg-card">
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full min-w-[620px] text-left text-[13px]">
              <thead className="bg-muted/60 text-[11px] uppercase tracking-wide text-muted-foreground">
                <tr><th className="px-3 py-2.5">Candidate</th><th className="px-3 py-2.5">Position</th><th className="px-3 py-2.5">Deleted</th><th className="px-3 py-2.5">Status</th></tr>
              </thead>
              <tbody className="divide-y divide-border">
                {deletedCandidates.map((candidate) => (
                  <tr key={candidate.id} className="hover:bg-muted/30">
                    <td className="px-3 py-2.5"><a className="inline-flex min-h-11 items-center font-semibold hover:text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30" href={candidateHref(candidate.id)} onClick={() => rememberRecruitmentReturn("trash")}>{candidate.full_name}</a><p className="text-xs text-muted-foreground">{candidate.phone || "No phone"}</p></td>
                    <td className="px-3 py-2.5">{candidate.applied_position || candidate.subject || "—"}</td>
                    <td className="px-3 py-2.5">{dateLabel(candidate.stage_changed_at)}</td>
                    <td className="px-3 py-2.5"><StatusBadge status="trash_bin">Trash Bin</StatusBadge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="divide-y divide-border md:hidden">
            {deletedCandidates.map((candidate) => (
              <a key={candidate.id} href={candidateHref(candidate.id)} onClick={() => rememberRecruitmentReturn("trash")} className="block min-h-14 p-3 hover:bg-muted/40">
                <div className="flex items-start justify-between gap-2"><span className="text-sm font-semibold">{candidate.full_name}</span><StatusBadge status="trash_bin">Trash Bin</StatusBadge></div>
                <p className="mt-1 text-xs text-muted-foreground">{candidate.applied_position || "Position not set"}</p>
              </a>
            ))}
          </div>
          {!deletedCandidates.length ? <div className="p-4"><EmptyLine><span className="inline-flex items-center gap-2"><Trash2 className="h-4 w-4" />Trash Bin is empty.</span></EmptyLine></div> : null}
          <div className="p-3"><Pagination page={page} totalPages={candidates.data.total_pages} onPageChange={setPage} label={`${candidates.data.total} deleted candidates · Page ${page} of ${candidates.data.total_pages}`} /></div>
        </section>
      ) : null}
    </div>
  );
}
