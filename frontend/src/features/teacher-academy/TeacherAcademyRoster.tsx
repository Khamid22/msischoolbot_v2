import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowDownWideNarrow,
  ExternalLink,
  Loader2,
  Search,
  UserMinus,
} from "lucide-react";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
  type MouseEvent,
  type ReactNode,
  type RefObject,
} from "react";

import { jsonBody, recruitmentRequest } from "@/features/recruitment/api";
import { dateLabel, type RecruitmentOptions } from "@/features/recruitment/model";
import {
  RECRUITMENT_API,
  buttonClass,
  fieldClass,
  queryError,
  replaceUrlParams,
  secondaryButtonClass,
} from "@/features/recruitment/ui";
import { ActionMenu, type ActionMenuItem } from "@/shared/ui/ActionMenu";
import { MobileCardList } from "@/shared/ui/MobileCardList";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";
import { Pagination } from "@/shared/ui/Pagination";
import { ResponsiveTable } from "@/shared/ui/ResponsiveTable";

export type TeacherRosterKind = "teacher_academy" | "active_teacher";
export type TeacherRosterSort = "average_score" | "lessons" | "date";

export type TeacherRosterItem = {
  kind: TeacherRosterKind;
  record_id: number;
  recruitment_candidate_id: number;
  full_name: string;
  position: string;
  subject: string;
  status: string;
  onboarding_status: string;
  joined_at: string;
  added_on: string;
  assigned_count: number;
  passed_count: number;
  average_score: number | null;
  can_remove: boolean;
  generated_login_will_be_deleted: boolean;
};

type TeacherPage = {
  items: TeacherRosterItem[];
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
};

export function useCanonicalTeacherRosterTotals(refreshToken = "", enabled = true) {
  const academy = useQuery({
    queryKey: ["recruitment", "teachers", "totals", "teacher_academy", refreshToken],
    queryFn: () => recruitmentRequest<TeacherPage>(
      `${RECRUITMENT_API}/teachers?kind=teacher_academy&page=1&per_page=1&sort=average_score`,
    ),
    enabled,
  });
  const active = useQuery({
    queryKey: ["recruitment", "teachers", "totals", "active_teacher", refreshToken],
    queryFn: () => recruitmentRequest<TeacherPage>(
      `${RECRUITMENT_API}/teachers?kind=active_teacher&page=1&per_page=1&sort=date`,
    ),
    enabled,
  });
  return {
    teacher_academy: academy.data?.total ?? 0,
    active_teacher: active.data?.total ?? 0,
    isLoading: academy.isLoading || active.isLoading,
  };
}

type RemovalResult = {
  message: string;
  identity_deleted: boolean;
  already_removed: boolean;
};

type RosterMessageTone = "success" | "error";

type TeacherAcademyRosterProps = {
  kind: TeacherRosterKind;
  basePath?: string;
  refreshToken?: string;
  onOpenTeacher?: (teacher: TeacherRosterItem) => void;
  onRemoved?: (teacher: TeacherRosterItem) => void;
  onTotalChange?: (total: number) => void;
  onAnnouncement: (message: string, tone?: RosterMessageTone) => void;
  toolbarLeading?: ReactNode;
};

const DESKTOP_ROW_HEIGHT = 56;
const DESKTOP_HEADER_HEIGHT = 40;
const PAGINATION_HEIGHT = 48;
const VIEWPORT_GUTTER = 16;
const DESKTOP_MIN_PAGE_SIZE = 10;
const MOBILE_PAGE_SIZE = 5;

function statusLabel(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function initialRosterFilters() {
  if (typeof window === "undefined") {
    return {
      search: "",
      subjectId: "",
      sort: "average_score" as TeacherRosterSort,
      page: 1,
    };
  }
  const params = new URLSearchParams(window.location.search);
  const requestedSort = params.get("teacher_sort");
  const requestedPage = Number(params.get("teacher_page") || 1);
  return {
    search: params.get("teacher_search") || "",
    subjectId: params.get("teacher_subject") || "",
    sort: requestedSort === "lessons" || requestedSort === "date"
      ? requestedSort
      : "average_score" as TeacherRosterSort,
    page: Number.isFinite(requestedPage) && requestedPage > 0
      ? Math.floor(requestedPage)
      : 1,
  };
}

function profileHref(teacher: TeacherRosterItem, basePath: string) {
  return teacher.recruitment_candidate_id && basePath
    ? `${basePath}/candidates/${teacher.recruitment_candidate_id}?origin=teachers`
    : "";
}

function isInteractiveTarget(target: EventTarget | null) {
  return target instanceof Element
    && Boolean(target.closest("a,button,input,select,textarea,[role='menuitem']"));
}

function AcademyStatus({ status }: { status: string }) {
  const normalized = String(status || "").toLowerCase();
  const tone = normalized.includes("improvement")
    ? "bg-rose-100 text-rose-900"
    : normalized.includes("ready") || normalized.includes("passed")
      ? "bg-emerald-100 text-emerald-900"
      : "bg-sky-100 text-sky-900";
  return (
    <span className={`inline-flex rounded-full px-2 py-1 text-[11px] font-semibold ${tone}`}>
      {statusLabel(status || "in_training")}
    </span>
  );
}

function LessonsCompleted({ teacher }: { teacher: TeacherRosterItem }) {
  if (teacher.assigned_count <= 0) {
    return <span className="text-xs font-medium text-muted-foreground">Not started</span>;
  }
  return (
    <span className="text-xs font-semibold tabular-nums text-foreground">
      {teacher.passed_count}/{teacher.assigned_count}
    </span>
  );
}

function AverageScore({ teacher }: { teacher: TeacherRosterItem }) {
  return (
    <span className="text-xs font-semibold tabular-nums text-foreground">
      {teacher.average_score === null ? "No score" : teacher.average_score.toFixed(1)}
    </span>
  );
}

function useViewportPageSize(
  tableRef: RefObject<HTMLDivElement | null>,
) {
  const [perPage, setPerPage] = useState(() => (
    typeof window !== "undefined" && window.innerWidth < 1024
      ? MOBILE_PAGE_SIZE
      : DESKTOP_MIN_PAGE_SIZE
  ));

  useEffect(() => {
    let frame = 0;
    const calculate = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        if (window.matchMedia("(max-width: 1023px)").matches) {
          setPerPage(MOBILE_PAGE_SIZE);
          return;
        }
        const tableTop = tableRef.current?.getBoundingClientRect().top ?? 0;
        const viewportHeight = window.visualViewport?.height ?? window.innerHeight;
        const available = Math.max(
          DESKTOP_HEADER_HEIGHT + DESKTOP_ROW_HEIGHT,
          viewportHeight - Math.max(0, tableTop) - VIEWPORT_GUTTER,
        );
        const next = Math.max(
          DESKTOP_MIN_PAGE_SIZE,
          Math.min(
            100,
            Math.floor(
              (
                available
                - DESKTOP_HEADER_HEIGHT
                - PAGINATION_HEIGHT
              ) / DESKTOP_ROW_HEIGHT,
            ),
          ),
        );
        setPerPage(next);
      });
    };

    calculate();
    const observer = typeof ResizeObserver === "function"
      ? new ResizeObserver(calculate)
      : null;
    if (tableRef.current) observer?.observe(tableRef.current);
    window.addEventListener("resize", calculate);
    window.visualViewport?.addEventListener("resize", calculate);
    return () => {
      cancelAnimationFrame(frame);
      observer?.disconnect();
      window.removeEventListener("resize", calculate);
      window.visualViewport?.removeEventListener("resize", calculate);
    };
  }, [tableRef]);

  return perPage;
}

function TeacherMobileCard({
  teacher,
  onOpen,
  onRemove,
}: {
  teacher: TeacherRosterItem;
  onOpen: () => void;
  onRemove: () => void;
}) {
  const isAcademy = teacher.kind === "teacher_academy";
  const actions: ActionMenuItem[] = [
    {
      key: "open",
      label: "Open details",
      icon: <ExternalLink className="h-4 w-4" />,
      onClick: onOpen,
    },
  ];
  if (teacher.can_remove) {
    actions.push(
      { key: "remove-separator", separator: true },
      {
        key: "remove",
        label: "Remove from Teacher Academy",
        icon: <UserMinus className="h-4 w-4" />,
        danger: true,
        onClick: onRemove,
      },
    );
  }
  return (
    <article className="rounded-xl border border-border bg-card p-3 shadow-sm">
      <div className="flex items-start gap-2">
        <button
          type="button"
          onClick={onOpen}
          className="min-w-0 flex-1 rounded-md text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
        >
          <strong className="block truncate text-sm">{teacher.full_name}</strong>
          <span className="mt-0.5 block truncate text-xs text-muted-foreground">
            {teacher.position || "Position not set"}
          </span>
        </button>
        <ActionMenu label={`Actions for ${teacher.full_name}`} items={actions} />
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 text-xs">
        <div>
          <dt className="font-medium text-muted-foreground">
            {isAcademy ? "Added to Academy" : "Active since"}
          </dt>
          <dd className="mt-0.5 font-semibold">
            {teacher.added_on ? dateLabel(teacher.added_on) : "Not recorded"}
          </dd>
        </div>
        <div>
          <dt className="font-medium text-muted-foreground">Subject</dt>
          <dd className="mt-0.5 truncate font-semibold">{teacher.subject || "Not set"}</dd>
        </div>
        <div>
          <dt className="font-medium text-muted-foreground">
            {isAcademy ? "Academy status" : "Status"}
          </dt>
          <dd className="mt-1">
            {isAcademy
              ? <AcademyStatus status={teacher.status} />
              : statusLabel(teacher.status)}
          </dd>
        </div>
        {isAcademy ? (
          <>
            <div>
              <dt className="font-medium text-muted-foreground">Lessons completed</dt>
              <dd className="mt-1"><LessonsCompleted teacher={teacher} /></dd>
            </div>
            <div>
              <dt className="font-medium text-muted-foreground">Average score</dt>
              <dd className="mt-1"><AverageScore teacher={teacher} /></dd>
            </div>
          </>
        ) : null}
      </dl>
    </article>
  );
}

export function TeacherAcademyRoster({
  kind,
  basePath = "",
  refreshToken = "",
  onOpenTeacher,
  onRemoved,
  onTotalChange,
  onAnnouncement,
  toolbarLeading,
}: TeacherAcademyRosterProps) {
  const initial = useMemo(initialRosterFilters, []);
  const [search, setSearch] = useState(initial.search);
  const [subjectId, setSubjectId] = useState(initial.subjectId);
  const [sort, setSort] = useState<TeacherRosterSort>(
    kind === "teacher_academy" ? initial.sort : "date",
  );
  const [page, setPage] = useState(initial.page);
  const [knownTotal, setKnownTotal] = useState(0);
  const [removeTeacher, setRemoveTeacher] = useState<TeacherRosterItem | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const tableViewportRef = useRef<HTMLDivElement>(null);
  const previousPerPageRef = useRef(0);
  const perPage = useViewportPageSize(tableViewportRef);
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!previousPerPageRef.current) {
      previousPerPageRef.current = perPage;
      return;
    }
    if (previousPerPageRef.current === perPage) return;
    const firstItemOffset = (page - 1) * previousPerPageRef.current;
    previousPerPageRef.current = perPage;
    setPage(Math.floor(firstItemOffset / perPage) + 1);
  }, [page, perPage]);

  useEffect(() => {
    replaceUrlParams({
      teacher_sort: kind === "teacher_academy" && sort !== "average_score" ? sort : null,
      teacher_subject: subjectId || null,
      teacher_search: search || null,
      teacher_page: page > 1 ? String(page) : null,
    });
  }, [kind, page, search, sort, subjectId]);

  const options = useQuery({
    queryKey: ["recruitment", "options"],
    queryFn: () => recruitmentRequest<RecruitmentOptions>(`${RECRUITMENT_API}/options`),
  });
  const queryParams = new URLSearchParams({
    kind,
    page: String(page),
    per_page: String(perPage),
    search,
    sort: kind === "teacher_academy" ? sort : "date",
  });
  if (subjectId) queryParams.set("subject_id", subjectId);
  const teachers = useQuery({
    queryKey: [
      "recruitment",
      "teachers",
      kind,
      page,
      perPage,
      search,
      subjectId,
      sort,
      refreshToken,
    ],
    queryFn: () => recruitmentRequest<TeacherPage>(
      `${RECRUITMENT_API}/teachers?${queryParams.toString()}`,
    ),
  });
  const items = teachers.data?.items || [];

  useEffect(() => {
    const total = teachers.data?.total ?? 0;
    setKnownTotal(total);
    onTotalChange?.(total);
    const totalPages = teachers.data?.total_pages ?? 1;
    if (page > totalPages) setPage(totalPages);
  }, [onTotalChange, page, teachers.data?.total, teachers.data?.total_pages]);

  const remove = useMutation({
    mutationFn: (values: { rejection_reason: string; reason_detail: string }) =>
      recruitmentRequest<RemovalResult>(
        `${RECRUITMENT_API}/teachers/${removeTeacher?.record_id}/remove`,
        { method: "POST", body: jsonBody(values) },
      ),
    onSuccess: (result) => {
      const removedTeacher = removeTeacher;
      setRemoveTeacher(null);
      setRejectionReason("");
      onAnnouncement(result.message || "Teacher removed from Teacher Academy.", "success");
      if (removedTeacher) onRemoved?.(removedTeacher);
      void queryClient.invalidateQueries({ queryKey: ["recruitment", "teachers"] });
    },
    onError: (error) => onAnnouncement(queryError(error), "error"),
  });

  const openTeacher = (teacher: TeacherRosterItem) => {
    if (onOpenTeacher) {
      onOpenTeacher(teacher);
      return;
    }
    const href = profileHref(teacher, basePath);
    if (href) window.location.assign(href);
  };
  const handleRowClick = (
    event: MouseEvent<HTMLTableRowElement>,
    teacher: TeacherRosterItem,
  ) => {
    if (!isInteractiveTarget(event.target)) openTeacher(teacher);
  };
  const handleRowKeyboard = (
    event: KeyboardEvent<HTMLTableRowElement>,
    teacher: TeacherRosterItem,
  ) => {
    if (isInteractiveTarget(event.target) || !["Enter", " "].includes(event.key)) return;
    event.preventDefault();
    openTeacher(teacher);
  };
  const closeRemoval = () => {
    if (remove.isPending) return;
    setRemoveTeacher(null);
    setRejectionReason("");
    remove.reset();
  };
  const submitRemoval = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    remove.mutate({
      rejection_reason: String(form.get("rejection_reason") || ""),
      reason_detail: String(form.get("reason_detail") || "").trim(),
    });
  };
  const updateSearch = (value: string) => {
    setSearch(value);
    setPage(1);
  };
  const updateSubject = (value: string) => {
    setSubjectId(value);
    setPage(1);
  };
  const updateSort = (value: TeacherRosterSort) => {
    setSort(value);
    setPage(1);
  };
  const firstItem = knownTotal ? ((page - 1) * perPage) + 1 : 0;
  const lastItem = Math.min(knownTotal, (page - 1) * perPage + items.length);

  return (
    <div className="space-y-3">
      <div className={`flex flex-col gap-2 xl:flex-row xl:items-end ${
        toolbarLeading ? "border-b-2 border-amber-500" : ""
      }`}>
        {toolbarLeading ? (
          <div className="min-w-0 flex-1">{toolbarLeading}</div>
        ) : null}
        <div className={`grid shrink-0 gap-2 pb-2 sm:grid-cols-2 xl:pb-1 ${
          kind === "teacher_academy"
            ? "xl:grid-cols-[10.5rem_10.5rem_15rem]"
            : "xl:grid-cols-[10.5rem_15rem]"
        }`}>
          {kind === "teacher_academy" ? (
            <label className="relative">
              <span className="sr-only">Sort Teacher Academy teachers</span>
              <ArrowDownWideNarrow className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <select
                value={sort}
                onChange={(event) => updateSort(event.target.value as TeacherRosterSort)}
                className={`${fieldClass} min-h-11 pl-9 text-xs`}
                aria-label="Sort Teacher Academy teachers"
              >
                <option value="average_score">Average score</option>
                <option value="lessons">Lessons completed</option>
                <option value="date">Date added</option>
              </select>
            </label>
          ) : null}
          <label>
            <span className="sr-only">Filter teachers by subject</span>
            <select
              value={subjectId}
              onChange={(event) => updateSubject(event.target.value)}
              className={`${fieldClass} min-h-11 text-xs`}
              aria-label="Filter teachers by subject"
            >
              <option value="">All subjects</option>
              {(options.data?.subjects || []).map((subject) => (
                <option key={subject.id} value={subject.id}>{subject.name}</option>
              ))}
            </select>
          </label>
          <label className="relative sm:col-span-2 xl:col-span-1">
            <span className="sr-only">Search teachers</span>
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="search"
              value={search}
              onChange={(event) => updateSearch(event.target.value)}
              className={`${fieldClass} min-h-11 pl-9 text-xs`}
              placeholder="Search teachers"
            />
          </label>
        </div>
      </div>

      <div ref={tableViewportRef}>
        {teachers.isLoading ? (
          <div className="hidden overflow-hidden rounded-xl border border-border bg-card lg:block" aria-label="Loading teachers">
            <div className="h-10 animate-pulse border-b border-border bg-muted/60 motion-reduce:animate-none" />
            {Array.from({ length: perPage }, (_, row) => (
              <div key={row} className="h-14 animate-pulse border-b border-border/70 bg-muted/25 last:border-0 motion-reduce:animate-none" />
            ))}
          </div>
        ) : null}
        {teachers.error ? (
          <div role="alert" className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
            {queryError(teachers.error)}
          </div>
        ) : null}
        {!teachers.isLoading && !teachers.error ? (
          <>
            <ResponsiveTable
              showAt="lg"
              ariaLabel={kind === "teacher_academy" ? "Teacher Academy teachers" : "Active teachers"}
              className="overflow-x-auto overflow-y-visible"
            >
              <table className="w-full min-w-[880px] table-fixed border-collapse text-left">
                <thead className="bg-muted/80 text-[11px] uppercase tracking-wide text-muted-foreground">
                  <tr className="h-10">
                    <th scope="col" className="w-[23%] px-4 font-semibold">Teacher</th>
                    <th scope="col" className="w-[17%] px-3 font-semibold">
                      {kind === "teacher_academy" ? "Added to Teacher Academy" : "Active since"}
                    </th>
                    <th scope="col" className="w-[21%] px-3 font-semibold">Position</th>
                    <th scope="col" className="w-[15%] px-3 font-semibold">
                      {kind === "teacher_academy" ? "Academy status" : "Status"}
                    </th>
                    <th scope="col" className="w-[13%] px-3 font-semibold">Lessons completed</th>
                    <th scope="col" className="w-[11%] px-3 font-semibold">Average score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {items.map((teacher) => (
                    <tr
                      key={`${teacher.kind}:${teacher.record_id}`}
                      tabIndex={0}
                      onClick={(event) => handleRowClick(event, teacher)}
                      onKeyDown={(event) => handleRowKeyboard(event, teacher)}
                      className="group h-14 cursor-pointer bg-card transition-colors duration-150 hover:bg-muted/40 focus:outline-none focus-visible:bg-muted/50 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/30 motion-reduce:transition-none"
                    >
                      <td className="px-4 py-1.5">
                        <button
                          type="button"
                          onClick={() => openTeacher(teacher)}
                          className="block w-full rounded text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
                        >
                          <span className="block truncate text-sm font-semibold text-foreground group-hover:text-primary">
                            {teacher.full_name}
                          </span>
                          <span className="mt-0.5 block truncate text-xs text-muted-foreground">
                            {teacher.subject || "Subject not set"}
                          </span>
                        </button>
                      </td>
                      <td className="px-3 py-1.5 text-xs font-medium text-foreground">
                        {teacher.added_on ? dateLabel(teacher.added_on) : "Not recorded"}
                      </td>
                      <td className="px-3 py-1.5">
                        <span className="line-clamp-2 text-xs text-foreground">
                          {teacher.position || "Position not set"}
                        </span>
                      </td>
                      <td className="px-3 py-1.5">
                        {kind === "teacher_academy"
                          ? <AcademyStatus status={teacher.status} />
                          : <span className="text-xs font-medium">{statusLabel(teacher.status)}</span>}
                      </td>
                      <td className="px-3 py-1.5"><LessonsCompleted teacher={teacher} /></td>
                      <td className="px-3 py-1.5"><AverageScore teacher={teacher} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!items.length ? (
                <div className="border-t border-border p-8 text-center text-sm text-muted-foreground">
                  No teachers in this view.
                </div>
              ) : null}
            </ResponsiveTable>
            <MobileCardList hideAt="lg">
              {items.map((teacher) => (
                <TeacherMobileCard
                  key={`${teacher.kind}:${teacher.record_id}`}
                  teacher={teacher}
                  onOpen={() => openTeacher(teacher)}
                  onRemove={() => setRemoveTeacher(teacher)}
                />
              ))}
              {!items.length ? (
                <div className="rounded-xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
                  No teachers in this view.
                </div>
              ) : null}
            </MobileCardList>
            <Pagination
              page={page}
              totalPages={teachers.data?.total_pages || 1}
              onPageChange={setPage}
              label={`Showing ${firstItem}–${lastItem} of ${knownTotal}`}
            />
          </>
        ) : null}
      </div>

      <Modal
        open={Boolean(removeTeacher)}
        title="Remove from Teacher Academy"
        subtitle={removeTeacher?.full_name}
        onClose={closeRemoval}
        closeOnOutsideClick={!remove.isPending}
        closeOnEscape={!remove.isPending}
        size="sm"
      >
        <form onSubmit={submitRemoval}>
          <ModalBody className="grid gap-3">
            {remove.error ? (
              <div role="alert" className="rounded-lg border border-destructive/25 bg-destructive/10 p-3 text-xs text-destructive">
                {queryError(remove.error)}
              </div>
            ) : null}
            <label className="text-xs font-semibold">
              Rejection reason
              <select
                autoFocus
                required
                name="rejection_reason"
                value={rejectionReason}
                onChange={(event) => setRejectionReason(event.target.value)}
                className={`${fieldClass} mt-1`}
              >
                <option value="">Select a reason</option>
                {(options.data?.rejection_reason_options || []).map((reason) => (
                  <option key={reason.value} value={reason.value}>{reason.label}</option>
                ))}
              </select>
            </label>
            <label className="text-xs font-semibold">
              Explanation {rejectionReason === "other"
                ? <span className="text-destructive">(required)</span>
                : <span className="font-normal text-muted-foreground">(optional)</span>}
              <textarea
                name="reason_detail"
                required={rejectionReason === "other"}
                className={`${fieldClass} mt-1 min-h-24 resize-y`}
                placeholder="Add context for the rejection history"
              />
            </label>
            <p className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs leading-5 text-amber-950">
              The lifecycle profile, Academy lessons, assessments, documents, and audit history will be preserved.
              {removeTeacher?.generated_login_will_be_deleted
                ? " The Academy-generated login will be permanently deleted and must be provisioned again if the teacher is later accepted."
                : ""}
            </p>
          </ModalBody>
          <ModalFooter>
            <div className="flex justify-end gap-2">
              <button type="button" className={secondaryButtonClass} disabled={remove.isPending} onClick={closeRemoval}>
                Cancel
              </button>
              <button type="submit" className={`${buttonClass} !bg-destructive !text-destructive-foreground`} disabled={remove.isPending || options.isLoading}>
                {remove.isPending
                  ? <Loader2 className="h-4 w-4 animate-spin" />
                  : <UserMinus className="h-4 w-4" />}
                Remove teacher
              </button>
            </div>
          </ModalFooter>
        </form>
      </Modal>
    </div>
  );
}
