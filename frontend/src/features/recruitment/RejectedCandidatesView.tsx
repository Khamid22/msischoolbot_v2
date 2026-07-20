import { Ban, Filter, Search, UserMinus } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { ClosedCandidateActions } from "@/features/recruitment/ClosedCandidateActions";
import { recruitmentRequest } from "@/features/recruitment/api";
import { dateLabel, humanize, stageLabels, type RecruitmentCandidate, type RecruitmentOptions } from "@/features/recruitment/model";
import {
  RECRUITMENT_API,
  EmptyLine,
  PageState,
  fieldClass,
  queryError,
  rememberRecruitmentReturn,
  replaceUrlParams,
  restoreRecruitmentReturn,
  secondaryButtonClass,
} from "@/features/recruitment/ui";
import { useViewportPageSize } from "@/features/recruitment/useViewportPageSize";
import { Drawer } from "@/shared/ui/Drawer";
import { Pagination } from "@/shared/ui/Pagination";
import { StatusBadge } from "@/shared/ui/StatusBadge";

type RejectedData = {
  items: RecruitmentCandidate[];
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
};

type OutcomeTab = "rejected" | "candidate_withdrew";
type ClosedFilters = {
  position: string;
  source: string;
  closed_from: string;
  closed_to: string;
  origin_stage: string;
};
const emptyFilters: ClosedFilters = { position: "", source: "", closed_from: "", closed_to: "", origin_stage: "" };

type Props = {
  basePath: string;
  options?: RecruitmentOptions;
  onAnnouncement: (message: string, tone?: "success" | "error") => void;
};

export function RejectedCandidatesView({ basePath, options, onAnnouncement }: Props) {
  const initial = new URLSearchParams(window.location.search);
  const [tab, setTab] = useState<OutcomeTab>(initial.get("tab") === "candidate_withdrew" ? "candidate_withdrew" : "rejected");
  const [page, setPage] = useState(() => Math.max(1, Number(initial.get("page") || 1)));
  const [search, setSearch] = useState(initial.get("search") || "");
  const [subjectId, setSubjectId] = useState(initial.get("subject_id") || "");
  const [filters, setFilters] = useState<ClosedFilters>(() => ({
    position: initial.get("position") || "",
    source: initial.get("source") || "",
    closed_from: initial.get("closed_from") || "",
    closed_to: initial.get("closed_to") || "",
    origin_stage: initial.get("origin_stage") || "",
  }));
  const [draftFilters, setDraftFilters] = useState(filters);
  const [filterOpen, setFilterOpen] = useState(false);
  const tableRef = useRef<HTMLDivElement>(null);
  const previousPerPage = useRef(10);
  const perPage = useViewportPageSize(tableRef, 62);

  useEffect(() => {
    if (previousPerPage.current === perPage) return;
    const firstVisible = (page - 1) * previousPerPage.current;
    previousPerPage.current = perPage;
    setPage(Math.floor(firstVisible / perPage) + 1);
  }, [page, perPage]);

  const params = new URLSearchParams({ page: String(page), per_page: String(perPage), stage: tab });
  if (search) params.set("search", search);
  if (subjectId) params.set("subject_id", subjectId);
  Object.entries(filters).forEach(([key, value]) => { if (value) params.set(key, value); });
  const candidates = useQuery({
    queryKey: ["recruitment", "outcomes", tab, page, perPage, search, subjectId, filters],
    queryFn: () => recruitmentRequest<RejectedData>(`${RECRUITMENT_API}/candidates?${params}`),
  });

  useEffect(() => {
    replaceUrlParams({ tab, page, search, subject_id: subjectId, ...filters }, ["stage", "per_page"]);
  }, [filters, page, search, subjectId, tab]);
  useEffect(() => {
    if (candidates.data) restoreRecruitmentReturn("rejected");
  }, [candidates.data]);
  useEffect(() => {
    if (candidates.data && page > candidates.data.total_pages) setPage(candidates.data.total_pages);
  }, [candidates.data, page]);

  const switchTab = (next: OutcomeTab) => {
    setTab(next);
    setPage(1);
  };
  const filterCount = Object.values(filters).filter(Boolean).length;
  const returnParams = new URLSearchParams({ tab, page: String(page) });
  if (search) returnParams.set("search", search);
  if (subjectId) returnParams.set("subject_id", subjectId);
  Object.entries(filters).forEach(([key, value]) => { if (value) returnParams.set(key, value); });
  const returnQuery = encodeURIComponent(`?${returnParams.toString()}`);
  const candidateHref = (candidateId: number) => `${basePath}/candidates/${candidateId}?tab=hiring&origin=rejected&return=${returnQuery}`;

  return (
    <div className="space-y-2">
      <section className="rounded-xl border border-border bg-card p-2.5">
        <div className="flex flex-col gap-2 lg:flex-row lg:items-center">
          <div role="tablist" aria-label="Closed recruitment outcomes" className="inline-flex shrink-0 rounded-lg border border-border bg-muted/40 p-1">
            <button type="button" role="tab" aria-selected={tab === "rejected"} onClick={() => switchTab("rejected")} className={`min-h-9 rounded-md px-3 text-sm font-semibold ${tab === "rejected" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}>Rejected</button>
            <button type="button" role="tab" aria-selected={tab === "candidate_withdrew"} onClick={() => switchTab("candidate_withdrew")} className={`min-h-9 rounded-md px-3 text-sm font-semibold ${tab === "candidate_withdrew" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}>Withdrawn</button>
          </div>
          <label className="relative min-w-0 flex-1">
            <span className="sr-only">Search closed candidates</span>
            <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4" />
            <input className={`${fieldClass} pl-9`} value={search} onChange={(event) => { setPage(1); setSearch(event.target.value); }} placeholder="Search candidates" />
          </label>
          <select aria-label="Filter by subject" className={`${fieldClass} lg:w-52`} value={subjectId} onChange={(event) => { setPage(1); setSubjectId(event.target.value); }}>
            <option value="">All subjects</option>
            {options?.subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}
          </select>
          <button type="button" className={`${secondaryButtonClass} relative`} onClick={() => { setDraftFilters(filters); setFilterOpen(true); }}>
            <Filter className="h-4 w-4" />Filter
            {filterCount ? <span className="rounded-full bg-primary px-1.5 text-[10px] text-primary-foreground">{filterCount}</span> : null}
          </button>
        </div>
      </section>

      <div ref={tableRef}>
        {candidates.isLoading ? <PageState>Loading closed candidates…</PageState> : null}
        {candidates.error ? <PageState tone="error">{queryError(candidates.error)}</PageState> : null}
        {candidates.data ? (
          <section className="overflow-hidden rounded-xl border border-border bg-card">
            <div className="hidden lg:block">
              <table className="w-full table-fixed text-left text-[13px]">
                <thead className="bg-muted/60 text-[11px] uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="w-[20%] px-3 py-1.5">Candidate</th>
                    <th className="w-[13%] px-3 py-1.5">Failed / left at</th>
                    <th className="w-[22%] px-3 py-1.5">Reason</th>
                    <th className="w-[14%] px-3 py-1.5">Recorded by</th>
                    <th className="w-[12%] px-3 py-1.5">Recorded</th>
                    <th className="w-[19%] px-3 py-1.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {candidates.data.items.map((candidate) => (
                    <tr key={candidate.id} className="h-[62px] hover:bg-muted/30">
                      <td className="px-3 py-1"><a href={candidateHref(candidate.id)} onClick={() => rememberRecruitmentReturn("rejected")} className="block truncate font-semibold hover:text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30">{candidate.full_name}</a><p className="truncate text-[11px] text-muted-foreground">{candidate.applied_position || candidate.subject || "Position not set"}</p></td>
                      <td className="px-3 py-1"><StatusBadge status={candidate.decision_origin_stage || "new_candidate"}>{stageLabels[candidate.decision_origin_stage || ""] || humanize(candidate.decision_origin_stage || "Unknown")}</StatusBadge></td>
                      <td className="px-3 py-1"><p className="truncate">{candidate.rejection_reason ? humanize(candidate.rejection_reason) : candidate.decision_reason_detail || "No reason recorded"}</p>{candidate.rejection_reason && candidate.decision_reason_detail ? <p className="truncate text-[11px] text-muted-foreground">{candidate.decision_reason_detail}</p> : null}</td>
                      <td className="truncate px-3 py-1">{candidate.final_decision_actor || "System"}</td>
                      <td className="px-3 py-1 text-muted-foreground">{dateLabel(candidate.final_decision_at || candidate.stage_changed_at)}</td>
                      <td className="px-3 py-1"><ClosedCandidateActions candidate={candidate} onAnnouncement={onAnnouncement} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="divide-y divide-border lg:hidden">
              {candidates.data.items.map((candidate) => (
                <article key={candidate.id} className="p-3">
                  <a href={candidateHref(candidate.id)} onClick={() => rememberRecruitmentReturn("rejected")} className="block rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30">
                    <div className="flex items-start justify-between gap-2"><span className="text-sm font-semibold">{candidate.full_name}</span><StatusBadge status={tab}>{tab === "rejected" ? "Rejected" : "Withdrawn"}</StatusBadge></div>
                    <p className="mt-1 text-xs text-muted-foreground">From {stageLabels[candidate.decision_origin_stage || ""] || humanize(candidate.decision_origin_stage || "Unknown stage")}</p>
                    <p className="mt-1 line-clamp-2 text-[13px]">{candidate.rejection_reason ? humanize(candidate.rejection_reason) : candidate.decision_reason_detail || "No reason recorded"}</p>
                    <p className="mt-1 text-xs text-muted-foreground">By {candidate.final_decision_actor || "System"} · {dateLabel(candidate.final_decision_at || candidate.stage_changed_at)}</p>
                  </a>
                  <ClosedCandidateActions candidate={candidate} onAnnouncement={onAnnouncement} />
                </article>
              ))}
            </div>
            {!candidates.data.items.length ? <div className="p-3"><EmptyLine><span className="inline-flex items-center gap-2">{tab === "rejected" ? <Ban className="h-4 w-4" /> : <UserMinus className="h-4 w-4" />}{tab === "rejected" ? "No rejected candidates." : "No withdrawn candidates."}</span></EmptyLine></div> : null}
            <div className="border-t border-border p-2.5"><Pagination page={page} totalPages={candidates.data.total_pages} onPageChange={setPage} label={`${candidates.data.total} candidates · Page ${page} of ${candidates.data.total_pages}`} /></div>
          </section>
        ) : null}
      </div>

      <Drawer
        open={filterOpen}
        onClose={() => setFilterOpen(false)}
        title={`Filter ${tab === "rejected" ? "Rejected" : "Withdrawn"}`}
        footer={(
          <div className="flex justify-end gap-2">
            <button type="button" className={secondaryButtonClass} onClick={() => { setDraftFilters(emptyFilters); setFilters(emptyFilters); setPage(1); setFilterOpen(false); }}>Clear</button>
            <button type="button" className="inline-flex min-h-9 items-center rounded-lg bg-primary px-3 text-sm font-semibold text-primary-foreground" onClick={() => { setFilters(draftFilters); setPage(1); setFilterOpen(false); }}>Apply</button>
          </div>
        )}
      >
        <div className="grid gap-2">
          <label className="text-xs font-semibold">Position<select className={`${fieldClass} mt-1`} value={draftFilters.position} onChange={(event) => setDraftFilters({ ...draftFilters, position: event.target.value })}><option value="">All positions</option>{options?.option_categories.position?.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
          <label className="text-xs font-semibold">Source<select className={`${fieldClass} mt-1`} value={draftFilters.source} onChange={(event) => setDraftFilters({ ...draftFilters, source: event.target.value })}><option value="">All sources</option>{options?.sources.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
          <label className="text-xs font-semibold">Failed / left at<select className={`${fieldClass} mt-1`} value={draftFilters.origin_stage} onChange={(event) => setDraftFilters({ ...draftFilters, origin_stage: event.target.value })}><option value="">All stages</option>{Object.entries(stageLabels).filter(([value]) => !["trash_bin", "rejected", "candidate_withdrew"].includes(value)).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          <div className="grid grid-cols-2 gap-2">
            <label className="text-xs font-semibold">Recorded from<input type="date" className={`${fieldClass} mt-1`} value={draftFilters.closed_from} onChange={(event) => setDraftFilters({ ...draftFilters, closed_from: event.target.value })} /></label>
            <label className="text-xs font-semibold">Recorded to<input type="date" className={`${fieldClass} mt-1`} value={draftFilters.closed_to} onChange={(event) => setDraftFilters({ ...draftFilters, closed_to: event.target.value })} /></label>
          </div>
        </div>
      </Drawer>
    </div>
  );
}
