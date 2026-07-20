import { ListFilter, Search, X } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { recruitmentRequest } from "@/features/recruitment/api";
import { dateLabel, humanize, stageLabels, type RecruitmentCandidate, type RecruitmentOptions } from "@/features/recruitment/model";
import { RECRUITMENT_API, EmptyLine, PageState, fieldClass, queryError, rememberRecruitmentReturn, replaceUrlParams, restoreRecruitmentReturn, secondaryButtonClass } from "@/features/recruitment/ui";
import { Drawer } from "@/shared/ui/Drawer";
import { Pagination } from "@/shared/ui/Pagination";
import { StatusBadge } from "@/shared/ui/StatusBadge";

type CandidateListData = {
  items: RecruitmentCandidate[];
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
};

type CandidateFilters = {
  search: string;
  position: string;
  stage: string;
  source: string;
  subject_id: string;
  application_from: string;
  application_to: string;
  final_decision: string;
  evaluator_account_id: string;
};

const filterKeys: Array<keyof CandidateFilters> = [
  "search",
  "position",
  "stage",
  "source",
  "subject_id",
  "application_from",
  "application_to",
  "final_decision",
  "evaluator_account_id",
];

function initialFilters(): CandidateFilters {
  const params = new URLSearchParams(window.location.search);
  return Object.fromEntries(filterKeys.map((key) => [key, params.get(key) || ""])) as CandidateFilters;
}

function filterLabel(key: keyof CandidateFilters, value: string, options?: RecruitmentOptions) {
  if (key === "stage" || key === "final_decision") return stageLabels[value] || humanize(value);
  if (key === "evaluator_account_id") return options?.staff.find((person) => String(person.id) === value)?.name || `Evaluator ${value}`;
  if (key === "subject_id") return options?.subjects.find((subject) => String(subject.id) === value)?.name || `Subject ${value}`;
  if (key === "source") return options?.sources.find((source) => String(source.id) === value)?.label || value;
  if (key === "position") return options?.option_categories.position?.find((position) => String(position.id) === value)?.label || value;
  if (key === "application_from") return `From ${dateLabel(value)}`;
  if (key === "application_to") return `To ${dateLabel(value)}`;
  return value;
}

function AdvancedFilters({
  open,
  filters,
  options,
  onClose,
  onApply,
}: {
  open: boolean;
  filters: CandidateFilters;
  options?: RecruitmentOptions;
  onClose: () => void;
  onApply: (filters: CandidateFilters) => void;
}) {
  const [draft, setDraft] = useState(filters);
  useEffect(() => {
    if (open) setDraft(filters);
  }, [filters, open]);
  const update = (key: keyof CandidateFilters, value: string) => setDraft((current) => ({ ...current, [key]: value }));
  return (
    <Drawer
      open={open}
      onClose={onClose}
      title="Candidate filters"
      description="Narrow the list without losing your place."
      footer={(
        <div className="flex justify-end gap-2">
          <button type="button" className={secondaryButtonClass} onClick={onClose}>Cancel</button>
          <button type="button" className="inline-flex min-h-9 items-center justify-center rounded-lg bg-primary px-3 text-sm font-semibold text-primary-foreground" onClick={() => onApply(draft)}>Apply filters</button>
        </div>
      )}
    >
      <div className="grid gap-4">
        <label className="text-xs font-semibold">Position<select className={`${fieldClass} mt-1`} value={draft.position} onChange={(event) => update("position", event.target.value)}><option value="">All positions</option>{options?.option_categories.position?.map((position) => <option key={position.id} value={position.id}>{position.label}</option>)}</select></label>
        <label className="text-xs font-semibold">Source<select className={`${fieldClass} mt-1`} value={draft.source} onChange={(event) => update("source", event.target.value)}><option value="">All sources</option>{options?.sources.map((source) => <option key={source.id} value={source.id}>{source.label}</option>)}</select></label>
        <label className="text-xs font-semibold">Subject<select className={`${fieldClass} mt-1`} value={draft.subject_id} onChange={(event) => update("subject_id", event.target.value)}><option value="">All subjects</option>{options?.subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}</select></label>
        <label className="text-xs font-semibold">Final outcome<select className={`${fieldClass} mt-1`} value={draft.final_decision} onChange={(event) => update("final_decision", event.target.value)}><option value="">All outcomes</option>{["teacher_academy", "active_teacher", "rejected", "candidate_withdrew"].map((outcome) => <option key={outcome} value={outcome}>{stageLabels[outcome]}</option>)}</select></label>
        <div className="grid gap-2 sm:grid-cols-2">
          <label className="text-xs font-semibold">Applied from<input type="date" className={`${fieldClass} mt-1`} value={draft.application_from} onChange={(event) => update("application_from", event.target.value)} /></label>
          <label className="text-xs font-semibold">Applied to<input type="date" className={`${fieldClass} mt-1`} value={draft.application_to} onChange={(event) => update("application_to", event.target.value)} /></label>
        </div>
        <label className="text-xs font-semibold">Evaluator<select className={`${fieldClass} mt-1`} value={draft.evaluator_account_id} onChange={(event) => update("evaluator_account_id", event.target.value)}><option value="">All evaluators</option>{options?.staff.filter((person) => ["academic_director", "head_of_department"].includes(person.role)).map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}</select></label>
      </div>
    </Drawer>
  );
}

export function CandidateListView({ basePath }: { basePath: string }) {
  const [page, setPage] = useState(() => {
    const requestedPage = Number(new URLSearchParams(window.location.search).get("page") || 1);
    return Number.isFinite(requestedPage) && requestedPage > 0 ? Math.floor(requestedPage) : 1;
  });
  const [filters, setFilters] = useState<CandidateFilters>(initialFilters);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const options = useQuery({ queryKey: ["recruitment", "options"], queryFn: () => recruitmentRequest<RecruitmentOptions>(`${RECRUITMENT_API}/options`) });
  const params = new URLSearchParams({ page: String(page), per_page: "25" });
  Object.entries(filters).forEach(([key, value]) => { if (value) params.set(key, value); });
  const candidates = useQuery({
    queryKey: ["recruitment", "candidates", page, filters],
    queryFn: () => recruitmentRequest<CandidateListData>(`${RECRUITMENT_API}/candidates?${params}`),
  });

  useEffect(() => {
    replaceUrlParams({ page, ...filters }, ["per_page"]);
  }, [filters, page]);

  useEffect(() => {
    if (candidates.data) restoreRecruitmentReturn("candidates");
  }, [candidates.data]);

  const activeFilters = useMemo(
    () => filterKeys.filter((key) => Boolean(filters[key])),
    [filters],
  );
  const advancedCount = activeFilters.filter((key) => !["search", "stage"].includes(key)).length;
  const returnParams = new URLSearchParams({ page: String(page) });
  Object.entries(filters).forEach(([key, value]) => { if (value) returnParams.set(key, value); });
  const returnQuery = encodeURIComponent(`?${returnParams.toString()}`);
  const candidateHref = (candidateId: number) => `${basePath}/candidates/${candidateId}?tab=overview&origin=candidates&return=${returnQuery}`;
  const update = (key: keyof CandidateFilters, value: string) => {
    setPage(1);
    setFilters((current) => ({ ...current, [key]: value }));
  };
  const clearFilters = () => {
    setPage(1);
    setFilters(Object.fromEntries(filterKeys.map((key) => [key, ""])) as CandidateFilters);
  };

  return (
    <div className="space-y-2">
      <section className="rounded-xl border border-border bg-card p-3">
        <div className="grid gap-2 md:grid-cols-[minmax(220px,1fr)_220px_auto]">
          <label className="text-xs font-semibold text-muted-foreground">
            Search
            <span className="relative mt-1 block">
              <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4" />
              <input className={`${fieldClass} pl-9`} value={filters.search} onChange={(event) => update("search", event.target.value)} placeholder="Candidate name" />
            </span>
          </label>
          <label className="text-xs font-semibold text-muted-foreground">
            Stage
            <select className={`${fieldClass} mt-1`} value={filters.stage} onChange={(event) => update("stage", event.target.value)}>
              <option value="">All stages</option>
              {options.data?.stages.map((stage) => <option key={stage} value={stage}>{stageLabels[stage] || humanize(stage)}</option>)}
            </select>
          </label>
          <button type="button" className={`${secondaryButtonClass} self-end`} onClick={() => setFiltersOpen(true)}>
            <ListFilter className="h-4 w-4" /> Filters{advancedCount ? ` (${advancedCount})` : ""}
          </button>
        </div>
        {activeFilters.length ? (
          <div className="mt-3 flex flex-wrap items-center gap-2" aria-label="Active filters">
            {activeFilters.map((key) => (
              <button
                key={key}
                type="button"
                className="inline-flex min-h-9 items-center gap-1.5 rounded-full border border-border bg-muted/50 px-3 text-xs font-semibold hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
                onClick={() => update(key, "")}
                aria-label={`Remove ${humanize(key)} filter`}
              >
                <span className="max-w-48 truncate">{humanize(key)}: {filterLabel(key, filters[key], options.data)}</span>
                <X className="h-3.5 w-3.5" />
              </button>
            ))}
            <button type="button" className="min-h-9 rounded-lg px-2 text-xs font-semibold text-primary hover:underline" onClick={clearFilters}>Clear all</button>
          </div>
        ) : null}
      </section>

      {candidates.isLoading ? <PageState>Loading candidates…</PageState> : null}
      {candidates.error ? <PageState tone="error">{queryError(candidates.error)}</PageState> : null}
      {candidates.data ? (
        <section className="overflow-hidden rounded-xl border border-border bg-card">
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full min-w-[760px] text-left text-[13px]">
              <thead className="bg-muted/60 text-[11px] uppercase tracking-wide text-muted-foreground"><tr><th className="px-3 py-1.5">Candidate</th><th className="px-3 py-1.5">Position</th><th className="px-3 py-1.5">Stage</th><th className="px-3 py-1.5">Applied</th><th className="px-3 py-1.5">Next action</th></tr></thead>
              <tbody className="divide-y divide-border">{candidates.data.items.map((candidate) => <tr key={candidate.id} className="hover:bg-muted/30"><td className="px-3 py-1.5"><a className="inline-flex min-h-9 items-center font-semibold hover:text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30" href={candidateHref(candidate.id)} onClick={() => rememberRecruitmentReturn("candidates")}>{candidate.full_name}</a><p className="text-xs text-muted-foreground">{candidate.phone || "No phone"}</p></td><td className="px-3 py-1.5">{candidate.applied_position || candidate.subject || "—"}</td><td className="px-3 py-1.5"><StatusBadge status={candidate.status}>{stageLabels[candidate.status] || humanize(candidate.status)}</StatusBadge></td><td className="px-3 py-1.5">{dateLabel(candidate.application_date)}</td><td className="px-3 py-1.5">{candidate.next_task?.title || "—"}</td></tr>)}</tbody>
            </table>
          </div>
          <div className="divide-y divide-border md:hidden">{candidates.data.items.map((candidate) => <a key={candidate.id} href={candidateHref(candidate.id)} onClick={() => rememberRecruitmentReturn("candidates")} className="block min-h-14 p-3 hover:bg-muted/40"><div className="flex items-start justify-between gap-2"><span className="text-sm font-semibold">{candidate.full_name}</span><StatusBadge status={candidate.status}>{stageLabels[candidate.status]}</StatusBadge></div><p className="mt-1 text-xs text-muted-foreground">{candidate.applied_position || "Position not set"}</p></a>)}</div>
          {!candidates.data.items.length ? <div className="p-3"><EmptyLine>No candidates match these filters.</EmptyLine></div> : null}
          <div className="p-3"><Pagination page={page} totalPages={candidates.data.total_pages} onPageChange={setPage} label={`${candidates.data.total} candidates · Page ${page} of ${candidates.data.total_pages}`} /></div>
        </section>
      ) : null}

      <AdvancedFilters
        open={filtersOpen}
        filters={filters}
        options={options.data}
        onClose={() => setFiltersOpen(false)}
        onApply={(next) => {
          setPage(1);
          setFilters(next);
          setFiltersOpen(false);
        }}
      />
    </div>
  );
}
