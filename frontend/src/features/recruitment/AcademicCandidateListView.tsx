import {
  Ban,
  CheckCircle2,
  Clock3,
  ListFilter,
  Search,
  UserRound,
  X,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import {
  useEffect,
  useMemo,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
} from "react";

import { recruitmentRequest } from "@/features/recruitment/api";
import {
  dateTimeLabel,
  humanize,
  isDemoEvaluatorRole,
  type RecruitmentCandidate,
  type RecruitmentOptions,
} from "@/features/recruitment/model";
import {
  EmptyLine,
  PageState,
  RECRUITMENT_API,
  fieldClass,
  queryError,
  rememberRecruitmentReturn,
  replaceUrlParams,
  restoreRecruitmentReturn,
  secondaryButtonClass,
} from "@/features/recruitment/ui";
import { Drawer } from "@/shared/ui/Drawer";
import { Pagination } from "@/shared/ui/Pagination";
import { StatusBadge } from "@/shared/ui/StatusBadge";

type AcademicCandidateGroup = "new" | "successful" | "rejected";
type AcademicRecruitmentRole = "academic_director" | "head_of_department";

type AcademicCandidateListData = {
  items: RecruitmentCandidate[];
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
  group_counts: Record<AcademicCandidateGroup, number>;
};

type AcademicCandidateFilters = {
  search: string;
  position: string;
  subject_id: string;
  evaluator_account_id: string;
  relevant_from: string;
  relevant_to: string;
};

const candidateGroups = [
  {
    key: "new",
    label: "New Candidates",
    icon: Clock3,
    activeClass: "bg-amber-500 text-amber-950",
  },
  {
    key: "successful",
    label: "Successful Candidates",
    icon: CheckCircle2,
    activeClass: "bg-emerald-700 text-white",
  },
  {
    key: "rejected",
    label: "Rejected Candidates",
    icon: Ban,
    activeClass: "bg-destructive text-destructive-foreground",
  },
] as const;

const filterKeys: Array<keyof AcademicCandidateFilters> = [
  "search",
  "position",
  "subject_id",
  "evaluator_account_id",
  "relevant_from",
  "relevant_to",
];

function initialCandidateGroup(): AcademicCandidateGroup {
  const value = new URLSearchParams(window.location.search).get("candidate_group");
  return value === "successful" || value === "rejected" ? value : "new";
}

function initialFilters(): AcademicCandidateFilters {
  const params = new URLSearchParams(window.location.search);
  return Object.fromEntries(
    filterKeys.map((key) => [key, params.get(key) || ""]),
  ) as AcademicCandidateFilters;
}

function evaluationLabel(value?: string) {
  if (value === "passed") return "Passed";
  if (value === "failed") return "Failed";
  return "Not recorded";
}

function candidateStatus(
  candidate: RecruitmentCandidate,
  group: AcademicCandidateGroup,
) {
  if (group === "successful") return "Successful";
  if (group === "rejected")
    return candidate.decision_source_evaluation_type === "demo"
      ? "Demo failed"
      : "Subject test failed";
  if (candidate.latest_demo_result === "passed") return "Awaiting subject test";
  if (candidate.academic_demo_status === "in_progress") return "Demo in progress";
  return "Demo scheduled";
}

function candidateHref(
  basePath: string,
  candidateId: number,
  returnQuery: string,
  tab: "evaluations" | "hiring" = "evaluations",
) {
  return `${basePath}/candidates/${candidateId}?tab=${tab}&origin=candidates&return=${returnQuery}`;
}

function filterLabel(
  key: keyof AcademicCandidateFilters,
  value: string,
  options?: RecruitmentOptions,
) {
  if (key === "evaluator_account_id")
    return (
      options?.staff.find((person) => String(person.id) === value)?.name ||
      `Evaluator ${value}`
    );
  if (key === "subject_id")
    return (
      options?.subjects.find((subject) => String(subject.id) === value)?.name ||
      `Subject ${value}`
    );
  if (key === "position")
    return (
      options?.option_categories.position?.find(
        (position) => String(position.id) === value,
      )?.label || value
    );
  if (key === "relevant_from") return `From ${value}`;
  if (key === "relevant_to") return `To ${value}`;
  return value;
}

function AcademicCandidateFiltersDrawer({
  open,
  filters,
  options,
  onClose,
  onApply,
}: {
  open: boolean;
  filters: AcademicCandidateFilters;
  options?: RecruitmentOptions;
  onClose: () => void;
  onApply: (filters: AcademicCandidateFilters) => void;
}) {
  const [draft, setDraft] = useState(filters);
  useEffect(() => {
    if (open) setDraft(filters);
  }, [filters, open]);
  const update = (key: keyof AcademicCandidateFilters, value: string) =>
    setDraft((current) => ({ ...current, [key]: value }));

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title="Candidate filters"
      description="Filter this evaluation group without changing the selected tab."
      footer={
        <div className="flex justify-end gap-2">
          <button type="button" className={secondaryButtonClass} onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="inline-flex min-h-9 items-center justify-center rounded-lg bg-primary px-3 text-sm font-semibold text-primary-foreground"
            onClick={() => onApply(draft)}
          >
            Apply filters
          </button>
        </div>
      }
    >
      <div className="grid gap-4">
        <label className="text-xs font-semibold">
          Position
          <select
            className={`${fieldClass} mt-1`}
            value={draft.position}
            onChange={(event) => update("position", event.target.value)}
          >
            <option value="">All positions</option>
            {options?.option_categories.position?.map((position) => (
              <option key={position.id} value={position.id}>
                {position.label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs font-semibold">
          Subject
          <select
            className={`${fieldClass} mt-1`}
            value={draft.subject_id}
            onChange={(event) => update("subject_id", event.target.value)}
          >
            <option value="">All subjects</option>
            {options?.subjects.map((subject) => (
              <option key={subject.id} value={subject.id}>
                {subject.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs font-semibold">
          Evaluator
          <select
            className={`${fieldClass} mt-1`}
            value={draft.evaluator_account_id}
            onChange={(event) =>
              update("evaluator_account_id", event.target.value)
            }
          >
            <option value="">All evaluators</option>
            {options?.staff
              .filter((person) => isDemoEvaluatorRole(person.role))
              .map((person) => (
                <option key={person.id} value={person.id}>
                  {person.name}
                </option>
              ))}
          </select>
        </label>
        <fieldset>
          <legend className="text-xs font-semibold">Relevant date</legend>
          <div className="mt-1 grid gap-2 sm:grid-cols-2">
            <label className="text-xs text-muted-foreground">
              From
              <input
                type="date"
                className={`${fieldClass} mt-1`}
                value={draft.relevant_from}
                onChange={(event) => update("relevant_from", event.target.value)}
              />
            </label>
            <label className="text-xs text-muted-foreground">
              To
              <input
                type="date"
                className={`${fieldClass} mt-1`}
                value={draft.relevant_to}
                onChange={(event) => update("relevant_to", event.target.value)}
              />
            </label>
          </div>
        </fieldset>
      </div>
    </Drawer>
  );
}

export function AcademicCandidateListView({
  basePath,
  role,
}: {
  basePath: string;
  role: AcademicRecruitmentRole;
}) {
  const [group, setGroup] =
    useState<AcademicCandidateGroup>(initialCandidateGroup);
  const [page, setPage] = useState(() => {
    const value = Number(
      new URLSearchParams(window.location.search).get("page") || 1,
    );
    return Number.isFinite(value) && value > 0 ? Math.floor(value) : 1;
  });
  const [filters, setFilters] =
    useState<AcademicCandidateFilters>(initialFilters);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const options = useQuery({
    queryKey: ["recruitment", "options"],
    queryFn: () =>
      recruitmentRequest<RecruitmentOptions>(`${RECRUITMENT_API}/options`),
  });
  const params = new URLSearchParams({
    page: String(page),
    per_page: "25",
    candidate_group: group,
  });
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const candidates = useQuery({
    queryKey: ["recruitment", "academic-candidates", group, page, filters],
    queryFn: () =>
      recruitmentRequest<AcademicCandidateListData>(
        `${RECRUITMENT_API}/candidates?${params}`,
      ),
  });

  useEffect(() => {
    replaceUrlParams({ candidate_group: group, page, ...filters }, ["per_page"]);
  }, [filters, group, page]);
  useEffect(() => {
    if (candidates.data) restoreRecruitmentReturn("candidates");
  }, [candidates.data]);

  const activeAdvancedFilters = useMemo(
    () => filterKeys.filter((key) => key !== "search" && Boolean(filters[key])),
    [filters],
  );
  const returnParams = new URLSearchParams({
    candidate_group: group,
    page: String(page),
  });
  Object.entries(filters).forEach(([key, value]) => {
    if (value) returnParams.set(key, value);
  });
  const returnQuery = encodeURIComponent(`?${returnParams.toString()}`);
  const selectGroup = (next: AcademicCandidateGroup) => {
    setGroup(next);
    setPage(1);
  };
  const handleTabKeyDown = (
    event: ReactKeyboardEvent<HTMLButtonElement>,
    current: AcademicCandidateGroup,
  ) => {
    const currentIndex = candidateGroups.findIndex((item) => item.key === current);
    let nextIndex: number | null = null;
    if (event.key === "ArrowRight")
      nextIndex = (currentIndex + 1) % candidateGroups.length;
    if (event.key === "ArrowLeft")
      nextIndex =
        (currentIndex - 1 + candidateGroups.length) % candidateGroups.length;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = candidateGroups.length - 1;
    if (nextIndex === null) return;
    event.preventDefault();
    const next = candidateGroups[nextIndex].key;
    selectGroup(next);
    requestAnimationFrame(() =>
      document.getElementById(`academic-candidate-tab-${next}`)?.focus(),
    );
  };
  const clearFilters = () => {
    setPage(1);
    setFilters(
      Object.fromEntries(
        filterKeys.map((key) => [key, ""]),
      ) as AcademicCandidateFilters,
    );
  };
  const openCandidate = (candidate: RecruitmentCandidate) => {
    rememberRecruitmentReturn("candidates");
    window.location.assign(
      candidateHref(basePath, candidate.id, returnQuery, "evaluations"),
    );
  };

  return (
    <div className="min-w-0 space-y-3">
      <section
        className="overflow-x-auto rounded-xl border border-border bg-card px-2 pt-2"
        aria-label="Candidate evaluation groups"
      >
        <div
          className="flex min-w-max items-end"
          role="tablist"
          aria-label="Candidate status"
        >
          {candidateGroups.map((item, index) => {
            const active = group === item.key;
            const Icon = item.icon;
            return (
              <button
                id={`academic-candidate-tab-${item.key}`}
                key={item.key}
                type="button"
                role="tab"
                aria-selected={active}
                tabIndex={active ? 0 : -1}
                onClick={() => selectGroup(item.key)}
                onKeyDown={(event) => handleTabKeyDown(event, item.key)}
                className={`relative inline-flex min-h-11 items-center gap-2 px-4 py-2 text-sm font-semibold transition-colors duration-200 focus:outline-none focus-visible:z-20 focus-visible:ring-2 focus-visible:ring-primary/40 motion-reduce:transition-none sm:min-w-48 ${
                  active
                    ? `z-10 ${item.activeClass}`
                    : "bg-muted/80 text-muted-foreground hover:bg-muted hover:text-foreground"
                } ${index === 0 ? "rounded-tl-lg" : ""}`}
                style={{
                  clipPath:
                    index === 0
                      ? "polygon(0 0, calc(100% - 1.25rem) 0, 100% 100%, 0 100%)"
                      : "polygon(0 0, calc(100% - 1.25rem) 0, 100% 100%, 1.25rem 100%)",
                  marginLeft: index ? "-0.625rem" : 0,
                  paddingLeft: index ? "1.875rem" : undefined,
                  paddingRight: "1.875rem",
                }}
              >
                <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                <span>{item.label}</span>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-bold tabular-nums ${
                    active ? "bg-white/55 text-slate-950" : "bg-background"
                  }`}
                >
                  {candidates.data?.group_counts?.[item.key] ?? 0}
                </span>
              </button>
            );
          })}
        </div>
      </section>

      <section className="rounded-xl border border-border bg-card p-3">
        <div className="grid gap-2 md:grid-cols-[minmax(13.75rem,1fr)_auto]">
          <label className="text-xs font-semibold text-muted-foreground">
            Search
            <span className="relative mt-1 block">
              <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4" />
              <input
                className={`${fieldClass} pl-9`}
                value={filters.search}
                onChange={(event) => {
                  setPage(1);
                  setFilters((current) => ({
                    ...current,
                    search: event.target.value,
                  }));
                }}
                placeholder="Candidate name"
              />
            </span>
          </label>
          <button
            type="button"
            className={`${secondaryButtonClass} self-end`}
            onClick={() => setFiltersOpen(true)}
          >
            <ListFilter className="h-4 w-4" />
            Filters
            {activeAdvancedFilters.length
              ? ` (${activeAdvancedFilters.length})`
              : ""}
          </button>
        </div>
        {activeAdvancedFilters.length ? (
          <div className="mt-3 flex flex-wrap items-center gap-2" aria-label="Active filters">
            {activeAdvancedFilters.map((key) => (
              <button
                key={key}
                type="button"
                className="inline-flex min-h-9 items-center gap-1.5 rounded-full border border-border bg-muted/50 px-3 text-xs font-semibold hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
                onClick={() => {
                  setPage(1);
                  setFilters((current) => ({ ...current, [key]: "" }));
                }}
                aria-label={`Remove ${humanize(key)} filter`}
              >
                <span className="max-w-48 truncate">
                  {filterLabel(key, filters[key], options.data)}
                </span>
                <X className="h-3.5 w-3.5" />
              </button>
            ))}
            <button
              type="button"
              className="min-h-9 rounded-lg px-2 text-xs font-semibold text-primary hover:underline"
              onClick={clearFilters}
            >
              Clear all
            </button>
          </div>
        ) : null}
      </section>

      {candidates.isLoading ? <PageState>Loading candidates…</PageState> : null}
      {candidates.error ? (
        <PageState tone="error">{queryError(candidates.error)}</PageState>
      ) : null}
      {candidates.data ? (
        <section
          id={`academic-candidate-panel-${group}`}
          role="tabpanel"
          aria-labelledby={`academic-candidate-tab-${group}`}
          className="overflow-hidden rounded-xl border border-border bg-card"
        >
          <div className="hidden overflow-x-auto lg:block">
            <table className="w-full min-w-[68rem] text-left text-[0.8125rem]">
              <thead className="bg-muted/60 text-[0.6875rem] uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-3 py-2">Candidate</th>
                  <th className="px-3 py-2">Subject / Position</th>
                  <th className="px-3 py-2">Demo</th>
                  <th className="px-3 py-2">Subject Test</th>
                  <th className="px-3 py-2">Evaluator</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Relevant Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {candidates.data.items.map((candidate) => {
                  const approval = candidate.actionable_approval;
                  const reviewHref = candidateHref(
                    basePath,
                    candidate.id,
                    returnQuery,
                    "hiring",
                  );
                  return (
                    <tr
                      key={candidate.id}
                      role="link"
                      tabIndex={0}
                      aria-label={`Open evaluations for ${candidate.full_name}`}
                      className="cursor-pointer transition-colors hover:bg-muted/35 focus:outline-none focus-visible:bg-primary/5 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/30"
                      onClick={() => openCandidate(candidate)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") openCandidate(candidate);
                      }}
                    >
                      <td className="px-3 py-2">
                        <span className="font-semibold text-foreground">
                          {candidate.full_name}
                        </span>
                        <span className="mt-0.5 block text-xs text-muted-foreground">
                          {candidate.phone || "No phone"}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <span className="font-medium">
                          {candidate.subject || "Subject not set"}
                        </span>
                        <span className="mt-0.5 block text-xs text-muted-foreground">
                          {candidate.applied_position || "Position not set"}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <StatusBadge
                          status={
                            candidate.academic_demo_status ||
                            candidate.latest_demo_result ||
                            "pending"
                          }
                        >
                          {candidate.academic_demo_status
                            ? humanize(candidate.academic_demo_status)
                            : evaluationLabel(candidate.latest_demo_result)}
                        </StatusBadge>
                      </td>
                      <td className="px-3 py-2">
                        <StatusBadge
                          status={candidate.latest_subject_test_result || "pending"}
                        >
                          {evaluationLabel(candidate.latest_subject_test_result)}
                        </StatusBadge>
                      </td>
                      <td className="px-3 py-2">
                        <span className="inline-flex items-center gap-1.5">
                          <UserRound className="h-4 w-4 text-muted-foreground" />
                          {candidate.evaluation_evaluator_name || "Not assigned"}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <StatusBadge status={group}>
                            {candidateStatus(candidate, group)}
                          </StatusBadge>
                          {role === "academic_director" &&
                          approval?.status === "requested" ? (
                            <>
                              <span className="rounded-full border border-amber-300 bg-amber-50 px-2 py-1 text-[0.6875rem] font-semibold text-amber-800 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-200">
                                Approval requested
                              </span>
                              <a
                                href={reviewHref}
                                onClick={(event) => {
                                  event.stopPropagation();
                                  rememberRecruitmentReturn("candidates");
                                }}
                                onKeyDown={(event) => event.stopPropagation()}
                                className="inline-flex min-h-9 items-center rounded-lg bg-primary px-2.5 text-xs font-semibold text-primary-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                              >
                                Review
                              </a>
                            </>
                          ) : null}
                          {role === "academic_director" &&
                          approval?.status === "approved" ? (
                            <span className="rounded-full border border-blue-300 bg-blue-50 px-2 py-1 text-[0.6875rem] font-semibold text-blue-700 dark:border-blue-500/40 dark:bg-blue-500/10 dark:text-blue-200">
                              Awaiting CEO
                            </span>
                          ) : null}
                        </div>
                      </td>
                      <td className="px-3 py-2 font-medium tabular-nums">
                        {dateTimeLabel(candidate.relevant_at)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="divide-y divide-border lg:hidden">
            {candidates.data.items.map((candidate) => {
              const approval = candidate.actionable_approval;
              return (
                <article key={candidate.id} className="p-3">
                  <a
                    href={candidateHref(
                      basePath,
                      candidate.id,
                      returnQuery,
                      "evaluations",
                    )}
                    onClick={() => rememberRecruitmentReturn("candidates")}
                    className="block rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <h3 className="truncate text-sm font-semibold">
                          {candidate.full_name}
                        </h3>
                        <p className="mt-0.5 truncate text-xs text-muted-foreground">
                          {candidate.subject ||
                            candidate.applied_position ||
                            "Subject not set"}
                        </p>
                      </div>
                      <StatusBadge status={group}>
                        {candidateStatus(candidate, group)}
                      </StatusBadge>
                    </div>
                    <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
                      <div className="rounded-lg bg-muted/45 p-2">
                        <dt className="text-muted-foreground">Demo</dt>
                        <dd className="mt-1 font-semibold">
                          {candidate.academic_demo_status
                            ? humanize(candidate.academic_demo_status)
                            : evaluationLabel(candidate.latest_demo_result)}
                        </dd>
                      </div>
                      <div className="rounded-lg bg-muted/45 p-2">
                        <dt className="text-muted-foreground">Subject test</dt>
                        <dd className="mt-1 font-semibold">
                          {evaluationLabel(candidate.latest_subject_test_result)}
                        </dd>
                      </div>
                      <div className="rounded-lg bg-muted/45 p-2">
                        <dt className="text-muted-foreground">Evaluator</dt>
                        <dd className="mt-1 truncate font-semibold">
                          {candidate.evaluation_evaluator_name || "Not assigned"}
                        </dd>
                      </div>
                      <div className="rounded-lg bg-muted/45 p-2">
                        <dt className="text-muted-foreground">Relevant date</dt>
                        <dd className="mt-1 font-semibold tabular-nums">
                          {dateTimeLabel(candidate.relevant_at)}
                        </dd>
                      </div>
                    </dl>
                  </a>
                  {role === "academic_director" &&
                  approval?.status === "requested" ? (
                    <div className="mt-2 flex items-center gap-2">
                      <span className="flex min-h-9 flex-1 items-center justify-center rounded-lg border border-amber-300 bg-amber-50 px-2 text-center text-xs font-semibold text-amber-800 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-200">
                        Approval requested
                      </span>
                      <a
                        href={candidateHref(
                          basePath,
                          candidate.id,
                          returnQuery,
                          "hiring",
                        )}
                        onClick={() => rememberRecruitmentReturn("candidates")}
                        className="inline-flex min-h-9 items-center justify-center rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground"
                      >
                        Review
                      </a>
                    </div>
                  ) : null}
                  {role === "academic_director" &&
                  approval?.status === "approved" ? (
                    <p className="mt-2 rounded-lg border border-blue-300 bg-blue-50 px-3 py-2 text-center text-xs font-semibold text-blue-700 dark:border-blue-500/40 dark:bg-blue-500/10 dark:text-blue-200">
                      Awaiting CEO finalization
                    </p>
                  ) : null}
                </article>
              );
            })}
          </div>

          {!candidates.data.items.length ? (
            <div className="p-3">
              <EmptyLine>
                No {candidateGroups.find((item) => item.key === group)?.label.toLowerCase()} match these filters.
              </EmptyLine>
            </div>
          ) : null}
          <div className="border-t border-border p-3">
            <Pagination
              page={page}
              totalPages={candidates.data.total_pages}
              onPageChange={setPage}
              label={`${candidates.data.total} candidates · Page ${page} of ${candidates.data.total_pages}`}
            />
          </div>
        </section>
      ) : null}

      <AcademicCandidateFiltersDrawer
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
