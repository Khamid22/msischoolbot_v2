import { Filter, Loader2, Search, Trash2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { ClosedCandidateActions } from "@/features/recruitment/ClosedCandidateActions";
import { jsonBody, recruitmentRequest } from "@/features/recruitment/api";
import { dateLabel, recruitmentStageLabel, type RecruitmentCandidate, type RecruitmentOptions } from "@/features/recruitment/model";
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
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";
import { Pagination } from "@/shared/ui/Pagination";
import { StatusBadge } from "@/shared/ui/StatusBadge";

type TrashBinData = {
  items: RecruitmentCandidate[];
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
};

type ClosedFilters = {
  position: string;
  source: string;
  closed_from: string;
  closed_to: string;
  origin_stage: string;
};

const emptyFilters: ClosedFilters = {
  position: "",
  source: "",
  closed_from: "",
  closed_to: "",
  origin_stage: "",
};

type Props = {
  basePath: string;
  options?: RecruitmentOptions;
  onAnnouncement: (message: string, tone?: "success" | "error") => void;
};

export function TrashBinView({ basePath, options, onAnnouncement }: Props) {
  const initial = new URLSearchParams(window.location.search);
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
  const [emptyOpen, setEmptyOpen] = useState(false);
  const [emptyConfirmation, setEmptyConfirmation] = useState("");
  const tableRef = useRef<HTMLDivElement>(null);
  const previousPerPage = useRef(10);
  const perPage = useViewportPageSize(tableRef);
  const queryClient = useQueryClient();

  useEffect(() => {
    if (previousPerPage.current === perPage) return;
    const firstVisible = (page - 1) * previousPerPage.current;
    previousPerPage.current = perPage;
    setPage(Math.floor(firstVisible / perPage) + 1);
  }, [page, perPage]);

  const requestParams = new URLSearchParams({
    page: String(page),
    per_page: String(perPage),
    stage: "trash_bin",
  });
  if (search) requestParams.set("search", search);
  if (subjectId) requestParams.set("subject_id", subjectId);
  Object.entries(filters).forEach(([key, value]) => { if (value) requestParams.set(key, value); });

  const candidates = useQuery({
    queryKey: ["recruitment", "trash", page, perPage, search, subjectId, filters],
    queryFn: () => recruitmentRequest<TrashBinData>(`${RECRUITMENT_API}/candidates?${requestParams}`),
  });
  const emptyTrash = useMutation({
    mutationFn: () => recruitmentRequest<{ message: string }>(
      `${RECRUITMENT_API}/trash/purge`,
      { method: "POST", body: jsonBody({ confirmation: emptyConfirmation }) },
    ),
    onSuccess: (result) => {
      setEmptyOpen(false);
      setEmptyConfirmation("");
      setPage(1);
      onAnnouncement(result.message || "Trash Bin emptied.");
      void queryClient.invalidateQueries({ queryKey: ["recruitment"] });
    },
    onError: (error) => onAnnouncement(queryError(error), "error"),
  });

  useEffect(() => {
    replaceUrlParams(
      { page, search, subject_id: subjectId, ...filters },
      ["stage", "application_from", "application_to", "final_decision", "evaluator_account_id", "per_page"],
    );
  }, [filters, page, search, subjectId]);
  useEffect(() => {
    if (candidates.data) restoreRecruitmentReturn("trash");
  }, [candidates.data]);
  useEffect(() => {
    if (candidates.data && page > candidates.data.total_pages) setPage(candidates.data.total_pages);
  }, [candidates.data, page]);

  const deletedCandidates = candidates.data?.items || [];
  const filterCount = Object.values(filters).filter(Boolean).length;
  const returnParams = new URLSearchParams({ page: String(page) });
  if (search) returnParams.set("search", search);
  if (subjectId) returnParams.set("subject_id", subjectId);
  Object.entries(filters).forEach(([key, value]) => { if (value) returnParams.set(key, value); });
  const returnQuery = encodeURIComponent(`?${returnParams.toString()}`);
  const candidateHref = (candidateId: number) => `${basePath}/candidates/${candidateId}?tab=overview&origin=trash&return=${returnQuery}`;

  return (
    <div className="space-y-2">
      <section className="rounded-xl border border-border bg-card p-2.5">
        <div className="flex flex-col gap-2 md:flex-row md:items-center">
          <label className="relative min-w-0 flex-1">
            <span className="sr-only">Search deleted candidates</span>
            <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4" />
            <input
              className={`${fieldClass} pl-9`}
              value={search}
              onChange={(event) => { setPage(1); setSearch(event.target.value); }}
              placeholder="Search candidates"
            />
          </label>
          <select
            aria-label="Filter by subject"
            className={`${fieldClass} md:w-52`}
            value={subjectId}
            onChange={(event) => { setPage(1); setSubjectId(event.target.value); }}
          >
            <option value="">All subjects</option>
            {options?.subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}
          </select>
          <button type="button" className={`${secondaryButtonClass} relative`} onClick={() => { setDraftFilters(filters); setFilterOpen(true); }}>
            <Filter className="h-4 w-4" />Filter
            {filterCount ? <span className="rounded-full bg-primary px-1.5 text-[0.625rem] text-primary-foreground">{filterCount}</span> : null}
          </button>
          <button
            type="button"
            className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border border-destructive/30 px-3 text-sm font-semibold text-destructive hover:bg-destructive/10 disabled:opacity-50"
            disabled={!candidates.data?.total}
            onClick={() => setEmptyOpen(true)}
          >
            <Trash2 className="h-4 w-4" />Empty Trash Bin
          </button>
        </div>
      </section>

      <div ref={tableRef}>
        {candidates.isLoading ? <PageState>Loading Trash Bin…</PageState> : null}
        {candidates.error ? <PageState tone="error">{queryError(candidates.error)}</PageState> : null}
        {candidates.data ? (
          <section className="overflow-hidden rounded-xl border border-border bg-card">
            <div className="hidden lg:block">
              <table className="w-full table-fixed text-left text-[0.8125rem]">
                <thead className="bg-muted/60 text-[0.6875rem] uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="w-[25%] px-3 py-1.5">Candidate</th>
                    <th className="w-[18%] px-3 py-1.5">Position</th>
                    <th className="w-[15%] px-3 py-1.5">Deleted</th>
                    <th className="w-[15%] px-3 py-1.5">Previous stage</th>
                    <th className="w-[27%] px-3 py-1.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {deletedCandidates.map((candidate) => (
                    <tr key={candidate.id} className="h-[3.625rem] hover:bg-muted/30">
                      <td className="px-3 py-1">
                        <a className="block truncate font-semibold hover:text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30" href={candidateHref(candidate.id)} onClick={() => rememberRecruitmentReturn("trash")}>{candidate.full_name}</a>
                        <p className="truncate text-[0.6875rem] text-muted-foreground">{candidate.phone || "No phone"}</p>
                      </td>
                      <td className="truncate px-3 py-1">{candidate.applied_position || candidate.subject || "—"}</td>
                      <td className="px-3 py-1 text-muted-foreground">{dateLabel(candidate.stage_changed_at)}</td>
                      <td className="px-3 py-1"><StatusBadge status={candidate.restore_stage || "new_candidate"}>{recruitmentStageLabel(candidate.restore_stage || "new_candidate", options?.stage_labels)}</StatusBadge></td>
                      <td className="px-3 py-1"><ClosedCandidateActions candidate={candidate} onAnnouncement={onAnnouncement} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="divide-y divide-border lg:hidden">
              {deletedCandidates.map((candidate) => (
                <article key={candidate.id} className="p-3">
                  <a href={candidateHref(candidate.id)} onClick={() => rememberRecruitmentReturn("trash")} className="block rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30">
                    <div className="flex items-start justify-between gap-2"><span className="text-sm font-semibold">{candidate.full_name}</span><StatusBadge status="trash_bin">Trash Bin</StatusBadge></div>
                    <p className="mt-1 text-xs text-muted-foreground">{candidate.applied_position || "Position not set"} · Deleted {dateLabel(candidate.stage_changed_at)}</p>
                  </a>
                  <ClosedCandidateActions candidate={candidate} onAnnouncement={onAnnouncement} />
                </article>
              ))}
            </div>
            {!deletedCandidates.length ? <div className="p-3"><EmptyLine><span className="inline-flex items-center gap-2"><Trash2 className="h-4 w-4" />Trash Bin is empty.</span></EmptyLine></div> : null}
            <div className="border-t border-border p-2.5"><Pagination page={page} totalPages={candidates.data.total_pages} onPageChange={setPage} label={`${candidates.data.total} deleted candidates · Page ${page} of ${candidates.data.total_pages}`} /></div>
          </section>
        ) : null}
      </div>

      <Drawer
        open={filterOpen}
        onClose={() => setFilterOpen(false)}
        title="Filter Trash Bin"
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
          <label className="text-xs font-semibold">Previous stage<select className={`${fieldClass} mt-1`} value={draftFilters.origin_stage} onChange={(event) => setDraftFilters({ ...draftFilters, origin_stage: event.target.value })}><option value="">All stages</option>{(options?.stage_definitions || []).filter((stage) => !["trash_bin", "rejected", "candidate_withdrew", "teacher_academy", "active_teacher"].includes(stage.stage_key)).map((stage) => <option key={stage.stage_key} value={stage.stage_key}>{stage.label}</option>)}</select></label>
          <div className="grid grid-cols-2 gap-2">
            <label className="text-xs font-semibold">Deleted from<input type="date" className={`${fieldClass} mt-1`} value={draftFilters.closed_from} onChange={(event) => setDraftFilters({ ...draftFilters, closed_from: event.target.value })} /></label>
            <label className="text-xs font-semibold">Deleted to<input type="date" className={`${fieldClass} mt-1`} value={draftFilters.closed_to} onChange={(event) => setDraftFilters({ ...draftFilters, closed_to: event.target.value })} /></label>
          </div>
        </div>
      </Drawer>

      <Modal open={emptyOpen} onClose={() => { if (!emptyTrash.isPending) { setEmptyOpen(false); setEmptyConfirmation(""); } }} title="Empty Trash Bin permanently?" size="sm" closeOnEscape={!emptyTrash.isPending} closeOnOutsideClick={!emptyTrash.isPending}>
        <ModalBody className="space-y-2">
          <div role="alert" className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
            Every candidate in Trash Bin and all of their recruitment data will be permanently deleted. This cannot be undone.
          </div>
          <label className="text-xs font-semibold">Type <strong>EMPTY TRASH BIN</strong> to confirm<input autoFocus className={`${fieldClass} mt-1`} value={emptyConfirmation} onChange={(event) => setEmptyConfirmation(event.target.value)} /></label>
        </ModalBody>
        <ModalFooter>
          <div className="flex justify-end gap-2">
            <button type="button" className={secondaryButtonClass} disabled={emptyTrash.isPending} onClick={() => setEmptyOpen(false)}>Cancel</button>
            <button type="button" className="inline-flex min-h-9 items-center gap-2 rounded-lg bg-destructive px-3 text-sm font-semibold text-destructive-foreground disabled:opacity-50" disabled={emptyConfirmation !== "EMPTY TRASH BIN" || emptyTrash.isPending} onClick={() => emptyTrash.mutate()}>{emptyTrash.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}Delete all permanently</button>
          </div>
        </ModalFooter>
      </Modal>
    </div>
  );
}
