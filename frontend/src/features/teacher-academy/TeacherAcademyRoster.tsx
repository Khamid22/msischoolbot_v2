import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Trash2, UserX } from "lucide-react";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
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
import {
  TeacherCardGrid,
  TeacherCardGridSkeleton,
  TeacherGridEmptyState,
  TeacherRosterToolbar,
  type TeacherAcademyCardModel,
} from "@/features/teacher-academy/TeacherAcademyCards";
import {
  academyRosterPageSize,
  academyStatusPresentation,
  type TeacherAcademySort,
} from "@/features/teacher-academy/model";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";
import { Pagination } from "@/shared/ui/Pagination";

export type TeacherRosterKind = "teacher_academy" | "active_teacher";
export type TeacherRosterSort = TeacherAcademySort;

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
  evaluated_count: number;
  passed_count: number;
  failed_count: number;
  average_score: number | null;
  academy_completed: boolean;
  can_remove: boolean;
  can_delete: boolean;
  can_reject: boolean;
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

type CloseResult = {
  message: string;
  action: "trash_bin" | "rejected";
  already_closed?: boolean;
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
  toolbarLayout?: "default" | "academy";
};

function initialRosterFilters() {
  if (typeof window === "undefined") {
    return { search: "", subjectId: "", sort: "average_score" as TeacherRosterSort, page: 1 };
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
    page: Number.isFinite(requestedPage) && requestedPage > 0 ? Math.floor(requestedPage) : 1,
  };
}

function profileHref(teacher: TeacherRosterItem, basePath: string) {
  return teacher.recruitment_candidate_id && basePath
    ? `${basePath}/candidates/${teacher.recruitment_candidate_id}?origin=teachers`
    : "";
}

function useResponsivePageSize() {
  const [pageSize, setPageSize] = useState(() => (
    academyRosterPageSize(typeof window === "undefined" ? 1280 : window.innerWidth)
  ));
  useEffect(() => {
    let frame = 0;
    const update = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => setPageSize(academyRosterPageSize(window.innerWidth)));
    };
    window.addEventListener("resize", update);
    window.visualViewport?.addEventListener("resize", update);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", update);
      window.visualViewport?.removeEventListener("resize", update);
    };
  }, []);
  return pageSize;
}

function useDebouncedValue(value: string, delay = 250) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timer);
  }, [delay, value]);
  return debounced;
}

function activeStatusLabel(value: string) {
  return String(value || "active")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
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
  toolbarLayout = "default",
}: TeacherAcademyRosterProps) {
  const initial = useMemo(initialRosterFilters, []);
  const [search, setSearch] = useState(initial.search);
  const debouncedSearch = useDebouncedValue(search);
  const [subjectId, setSubjectId] = useState(initial.subjectId);
  const [sort, setSort] = useState<TeacherRosterSort>(
    kind === "teacher_academy" ? initial.sort : "date",
  );
  const [page, setPage] = useState(initial.page);
  const [knownTotal, setKnownTotal] = useState(0);
  const [closeSelection, setCloseSelection] = useState<{
    teacher: TeacherRosterItem;
    action: "trash_bin" | "rejected";
  } | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const perPage = useResponsivePageSize();
  const previousPageSize = useRef(perPage);
  const queryClient = useQueryClient();

  useEffect(() => {
    replaceUrlParams({
      teacher_sort: kind === "teacher_academy" && sort !== "average_score" ? sort : null,
      teacher_subject: subjectId || null,
      teacher_search: search || null,
      teacher_page: page > 1 ? String(page) : null,
    });
  }, [kind, page, search, sort, subjectId]);

  useEffect(() => {
    if (previousPageSize.current === perPage) return;
    previousPageSize.current = perPage;
    setPage(1);
  }, [perPage]);

  useEffect(() => {
    setPage(1);
  }, [kind]);

  const options = useQuery({
    queryKey: ["recruitment", "options"],
    queryFn: () => recruitmentRequest<RecruitmentOptions>(`${RECRUITMENT_API}/options`),
  });
  const queryParams = new URLSearchParams({
    kind,
    page: String(page),
    per_page: String(perPage),
    search: debouncedSearch,
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
      debouncedSearch,
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

  const closeTeacher = useMutation({
    mutationFn: (values: {
      action: "trash_bin" | "rejected";
      rejection_reason: string;
      reason_detail: string;
    }) => recruitmentRequest<CloseResult>(
      `${RECRUITMENT_API}/teachers/${closeSelection?.teacher.kind}/${closeSelection?.teacher.record_id}/close`,
      { method: "POST", body: jsonBody(values) },
    ),
    onSuccess: (result) => {
      const closedTeacher = closeSelection?.teacher;
      setCloseSelection(null);
      setRejectionReason("");
      onAnnouncement(
        result.message || (result.action === "trash_bin" ? "Teacher moved to Trash Bin." : "Teacher rejected."),
        "success",
      );
      if (closedTeacher) onRemoved?.(closedTeacher);
      void queryClient.invalidateQueries({ queryKey: ["recruitment", "teachers"] });
      void queryClient.invalidateQueries({ queryKey: ["recruitment", "candidates"] });
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
  const closeAction = () => {
    if (closeTeacher.isPending) return;
    setCloseSelection(null);
    setRejectionReason("");
    closeTeacher.reset();
  };
  const submitAction = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    if (!closeSelection) return;
    closeTeacher.mutate({
      action: closeSelection.action,
      rejection_reason: closeSelection.action === "rejected"
        ? String(form.get("rejection_reason") || "")
        : "",
      reason_detail: String(form.get("reason_detail") || "").trim(),
    });
  };

  const clearFilters = () => {
    setSearch("");
    setSubjectId("");
    setSort(kind === "teacher_academy" ? "average_score" : "date");
    setPage(1);
  };
  const hasFilters = Boolean(search || subjectId || (kind === "teacher_academy" && sort !== "average_score"));
  const firstItem = knownTotal ? ((page - 1) * perPage) + 1 : 0;
  const lastItem = Math.min(knownTotal, (page - 1) * perPage + items.length);

  const cards: TeacherAcademyCardModel[] = items.map((teacher) => {
    const academyStatus = academyStatusPresentation(teacher.status);
    const actions = [];
    if (teacher.can_delete) {
      actions.push({
        key: "delete",
        label: "Delete to Trash Bin",
        icon: <Trash2 className="h-4 w-4" />,
        onClick: () => setCloseSelection({ teacher, action: "trash_bin" }),
        danger: true,
      });
    }
    if (teacher.can_reject) {
      actions.push({
        key: "reject",
        label: "Reject teacher",
        icon: <UserX className="h-4 w-4" />,
        onClick: () => setCloseSelection({ teacher, action: "rejected" }),
        danger: true,
      });
    }
    return {
      key: `${teacher.kind}:${teacher.record_id}`,
      kind: teacher.kind,
      fullName: teacher.full_name || "Teacher",
      position: teacher.position || (teacher.kind === "teacher_academy" ? "Trainee Teacher" : "Teacher"),
      subject: teacher.subject || "Subject not set",
      statusLabel: teacher.kind === "teacher_academy" ? academyStatus.label : activeStatusLabel(teacher.status),
      statusTone: teacher.kind === "teacher_academy" ? academyStatus.tone : "success",
      joinedLabel: teacher.added_on ? dateLabel(teacher.added_on) : "Not recorded",
      passed: teacher.passed_count,
      target: teacher.assigned_count,
      averageScore: teacher.average_score,
      completed: teacher.academy_completed,
      primaryLabel: teacher.kind === "teacher_academy" ? "View journey" : "View profile",
      onOpen: () => openTeacher(teacher),
      actions,
    };
  });

  return (
    <div className="space-y-2">
      <TeacherRosterToolbar
        search={search}
        subjectId={subjectId}
        sort={sort}
        subjects={(options.data?.subjects || []).map((subject) => ({ id: subject.id, label: subject.name }))}
        showSort={kind === "teacher_academy"}
        leading={toolbarLeading}
        layout={toolbarLayout}
        onSearchChange={(value) => {
          setSearch(value);
          setPage(1);
        }}
        onSubjectChange={(value) => {
          setSubjectId(value);
          setPage(1);
        }}
        onSortChange={(value) => {
          setSort(value);
          setPage(1);
        }}
        onClear={clearFilters}
      />

      <div
        id={toolbarLayout === "academy" && toolbarLeading ? "academy-roster-results" : undefined}
        role={toolbarLayout === "academy" && toolbarLeading ? "tabpanel" : undefined}
        aria-labelledby={toolbarLayout === "academy" && toolbarLeading ? `academy-tab-${kind === "active_teacher" ? "active_teachers" : "teacher_academy"}` : undefined}
        tabIndex={toolbarLayout === "academy" && toolbarLeading ? 0 : undefined}
        className="space-y-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
      >
        {teachers.isLoading ? <TeacherCardGridSkeleton count={perPage} /> : null}
        {teachers.error ? (
          <div role="alert" className="rounded-2xl border border-destructive/30 bg-destructive/10 p-5 text-sm text-destructive">
            <p className="font-bold">{queryError(teachers.error)}</p>
            <button
              type="button"
              onClick={() => void teachers.refetch()}
              className="mt-3 inline-flex min-h-11 items-center justify-center rounded-xl border border-destructive/30 bg-card px-4 font-black text-destructive hover:bg-destructive/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-destructive/35"
            >
              Try again
            </button>
          </div>
        ) : null}
        {!teachers.isLoading && !teachers.error ? (
          cards.length ? <TeacherCardGrid teachers={cards} /> : (
            <TeacherGridEmptyState filtered={hasFilters} onClear={clearFilters} />
          )
        ) : null}

        {!teachers.isLoading && !teachers.error && knownTotal ? (
          <Pagination
            page={page}
            totalPages={teachers.data?.total_pages || 1}
            onPageChange={setPage}
            label={`Showing ${firstItem}–${lastItem} of ${knownTotal}`}
          />
        ) : null}
      </div>

      <Modal
        open={Boolean(closeSelection)}
        title={closeSelection?.action === "trash_bin" ? "Delete to Trash Bin" : "Reject teacher"}
        subtitle={closeSelection?.teacher.full_name}
        onClose={closeAction}
        closeOnOutsideClick={!closeTeacher.isPending}
        closeOnEscape={!closeTeacher.isPending}
        size="sm"
      >
        <form onSubmit={submitAction}>
          <ModalBody className="grid gap-3">
            {closeTeacher.error ? (
              <div role="alert" className="rounded-lg border border-destructive/25 bg-destructive/10 p-3 text-xs text-destructive">
                {queryError(closeTeacher.error)}
              </div>
            ) : null}
            {closeSelection?.action === "rejected" ? (
              <>
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
              </>
            ) : (
              <input autoFocus className="sr-only" aria-label="Confirm delete to Trash Bin" />
            )}
            <p className="rounded-lg border border-warning/35 bg-warning/10 p-3 text-xs leading-5 text-warning-foreground">
              {closeSelection?.action === "trash_bin"
                ? "This removes the teacher from the active roster and disables their login. The profile can be recovered from Trash Bin."
                : "This moves the profile to Rejected. Lessons, assessments, documents, and audit history remain preserved."}
              {closeSelection?.action === "rejected" && closeSelection.teacher.generated_login_will_be_deleted
                ? " The Academy-generated login will be deleted and must be provisioned again if the teacher is accepted later."
                : ""}
            </p>
          </ModalBody>
          <ModalFooter>
            <div className="flex justify-end gap-2">
              <button type="button" className={secondaryButtonClass} disabled={closeTeacher.isPending} onClick={closeAction}>
                Cancel
              </button>
              <button type="submit" className={`${buttonClass} !bg-destructive !text-destructive-foreground`} disabled={closeTeacher.isPending || (closeSelection?.action === "rejected" && options.isLoading)}>
                {closeTeacher.isPending
                  ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" />
                  : closeSelection?.action === "trash_bin"
                    ? <Trash2 className="h-4 w-4" />
                    : <UserX className="h-4 w-4" />}
                {closeSelection?.action === "trash_bin" ? "Delete to Trash Bin" : "Reject teacher"}
              </button>
            </div>
          </ModalFooter>
        </form>
      </Modal>
    </div>
  );
}
