import {
  AlertTriangle,
  Ban,
  CalendarClock,
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleDot,
  Clock3,
  ExternalLink,
  Filter,
  History,
  List,
  Loader2,
  Pencil,
  Play,
  UserX,
  X,
  XCircle,
} from "lucide-react";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useEffect, useMemo, useState, type FormEvent } from "react";

import { AppointmentForm } from "@/features/recruitment/AppointmentForm";
import { DemoSessionModal } from "@/features/recruitment/DemoSessionModal";
import { InterviewSessionModal } from "@/features/recruitment/InterviewSessionModal";
import {
  formValues,
  jsonBody,
  recruitmentRequest,
} from "@/features/recruitment/api";
import type {
  RecruitmentAppointment,
  RecruitmentCandidate,
  RecruitmentOptions,
  RecruitmentRole,
} from "@/features/recruitment/model";
import {
  RECRUITMENT_API,
  buttonClass,
  fieldClass,
  queryError,
  rememberRecruitmentReturn,
  replaceUrlParams,
  restoreRecruitmentReturn,
  secondaryButtonClass,
} from "@/features/recruitment/ui";
import {
  addDaysToDateKey,
  schoolDateKey,
  schoolDateKeyFromValue,
  schoolDayStartIso,
  schoolWeekBounds,
} from "@/shared/lib/schoolTime";
import { ActionMenu, type ActionMenuItem } from "@/shared/ui/ActionMenu";
import { Drawer } from "@/shared/ui/Drawer";
import type { FloatingToastTone } from "@/shared/ui/FloatingToast";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";

type ScheduleMode = "day" | "week";
type ScheduleSection = "queue" | "history";
type HistoryStatus = "" | "passed" | "failed" | "not_conducted";
type DisplayStatus =
  | "passed"
  | "failed"
  | "scheduled"
  | "in_progress"
  | "overdue"
  | "not_conducted";
type AppointmentData = {
  items: RecruitmentAppointment[];
  total: number;
  page: number;
  total_pages: number;
};
type MutationPayload = { message: string };
type ScheduleFilters = {
  appointmentType: string;
  staffId: string;
  historyStatus: HistoryStatus;
};

const historyStatuses = new Set<HistoryStatus>([
  "",
  "passed",
  "failed",
  "not_conducted",
]);
const queueStatusFilter = "scheduled,in_progress";
const historyStatusFilter = "passed,failed,not_conducted";

const scheduleDayFormatter = new Intl.DateTimeFormat("en", {
  weekday: "short",
  month: "short",
  day: "numeric",
  timeZone: "Asia/Tashkent",
});
const scheduleDateFormatter = new Intl.DateTimeFormat("en", {
  weekday: "long",
  month: "long",
  day: "numeric",
  year: "numeric",
  timeZone: "Asia/Tashkent",
});
const shortDateFormatter = new Intl.DateTimeFormat("en", {
  month: "short",
  day: "numeric",
  timeZone: "Asia/Tashkent",
});
const scheduleTimeFormatter = new Intl.DateTimeFormat("en", {
  hour: "numeric",
  minute: "2-digit",
  timeZone: "Asia/Tashkent",
});

const statusPresentation: Record<
  DisplayStatus,
  {
    label: string;
    edge: string;
    badge: string;
    icon: typeof CheckCircle2;
  }
> = {
  passed: {
    label: "Passed",
    edge: "border-l-emerald-500",
    badge:
      "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-500/40 dark:bg-emerald-950/30 dark:text-emerald-200",
    icon: CheckCircle2,
  },
  failed: {
    label: "Failed",
    edge: "border-l-red-500",
    badge:
      "border-red-200 bg-red-50 text-red-800 dark:border-red-500/40 dark:bg-red-950/30 dark:text-red-200",
    icon: XCircle,
  },
  scheduled: {
    label: "Scheduled",
    edge: "border-l-blue-500",
    badge:
      "border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-500/40 dark:bg-blue-950/30 dark:text-blue-200",
    icon: CalendarClock,
  },
  in_progress: {
    label: "In Progress",
    edge: "border-l-violet-500",
    badge:
      "border-violet-200 bg-violet-50 text-violet-800 dark:border-violet-500/40 dark:bg-violet-950/30 dark:text-violet-200",
    icon: CircleDot,
  },
  overdue: {
    label: "Overdue",
    edge: "border-l-amber-500",
    badge:
      "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-500/40 dark:bg-amber-950/30 dark:text-amber-100",
    icon: AlertTriangle,
  },
  not_conducted: {
    label: "Not Conducted",
    edge: "border-l-slate-400",
    badge:
      "border-slate-200 bg-slate-100 text-slate-700 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200",
    icon: Ban,
  },
};

function dateKeyValue(dateKey: string) {
  return new Date(`${dateKey}T12:00:00Z`);
}

function scheduleDayLabel(dateKey: string) {
  return scheduleDayFormatter.format(dateKeyValue(dateKey));
}

function scheduleDateLabel(dateKey: string) {
  return scheduleDateFormatter.format(dateKeyValue(dateKey));
}

function shortDateLabel(dateKey: string) {
  return shortDateFormatter.format(dateKeyValue(dateKey));
}

function appointmentTimeLabel(item: RecruitmentAppointment) {
  const startsAt = new Date(item.starts_at);
  return Number.isNaN(startsAt.getTime())
    ? "Time not set"
    : scheduleTimeFormatter.format(startsAt);
}

function appointmentTitle(item: RecruitmentAppointment) {
  return item.appointment_type === "job_interview"
    ? "Job Interview"
    : "Demo Lesson";
}

function displayStatus(item: RecruitmentAppointment): DisplayStatus {
  const provided = item.display_status?.toLowerCase();
  if (provided && provided in statusPresentation)
    return provided as DisplayStatus;
  if (item.evaluation_outcome === "passed") return "passed";
  if (item.evaluation_outcome === "failed") return "failed";
  if (item.status === "in_progress") return "in_progress";
  if (item.status === "cancelled" || item.status === "no_show")
    return "not_conducted";
  if (item.is_overdue) return "overdue";
  return "scheduled";
}

function buildAppointmentQuery({
  start,
  end,
  status,
  filters,
}: {
  start?: string;
  end?: string;
  status: string;
  filters: ScheduleFilters;
}) {
  const query = new URLSearchParams({
    page: "1",
    per_page: "500",
    status,
  });
  if (start) query.set("from", schoolDayStartIso(start));
  if (end) query.set("to", schoolDayStartIso(end));
  if (filters.appointmentType)
    query.set("appointment_type", filters.appointmentType);
  if (filters.staffId)
    query.set("responsible_account_id", filters.staffId);
  return query;
}

function appointmentSort(
  section: ScheduleSection,
  left: RecruitmentAppointment,
  right: RecruitmentAppointment,
) {
  if (section === "queue") {
    const leftPriority = displayStatus(left) === "in_progress" ? 0 : 1;
    const rightPriority = displayStatus(right) === "in_progress" ? 0 : 1;
    if (leftPriority !== rightPriority) return leftPriority - rightPriority;
    return new Date(left.starts_at).getTime() - new Date(right.starts_at).getTime();
  }
  return new Date(right.starts_at).getTime() - new Date(left.starts_at).getTime();
}

function AppointmentRow({
  item,
  basePath,
  canManage,
  compact = false,
  showDate = false,
  onEdit,
  onSession,
  onStatus,
}: {
  item: RecruitmentAppointment;
  basePath: string;
  canManage: boolean;
  compact?: boolean;
  showDate?: boolean;
  onEdit: (item: RecruitmentAppointment) => void;
  onSession: (item: RecruitmentAppointment) => void;
  onStatus: (
    item: RecruitmentAppointment,
    status: "cancelled" | "no_show",
  ) => void;
}) {
  const actions: ActionMenuItem[] =
    item.status === "scheduled" && canManage
      ? [
          {
            key: "edit",
            label: "Reschedule",
            icon: <Pencil className="h-4 w-4" />,
            onClick: () => onEdit(item),
          },
          {
            key: "no_show",
            label: "Mark no-show",
            icon: <UserX className="h-4 w-4" />,
            onClick: () => onStatus(item, "no_show"),
          },
          { separator: true, key: "separator" },
          {
            key: "cancel",
            label: "Cancel appointment",
            icon: <Ban className="h-4 w-4" />,
            danger: true,
            onClick: () => onStatus(item, "cancelled"),
          },
        ]
      : [];
  const candidateName = item.candidate_name || "Candidate";
  const effectiveStatus = displayStatus(item);
  const appearance = statusPresentation[effectiveStatus];
  const StatusIcon = appearance.icon;
  const evaluatorLabel =
    item.appointment_type === "demo_lesson"
      ? item.evaluated_by_name ||
        item.responsible_name ||
        "Evaluator not assigned"
      : item.responsible_name || "HR not assigned";
  const sessionLabel = item.can_resume
    ? "Resume"
    : item.can_start
      ? "Start"
      : "";
  const externalLocation = /^https?:\/\//i.test(item.location_or_link || "");

  if (compact) {
    return (
      <article
        className={`min-w-0 rounded-lg border border-l-4 border-border bg-card p-2.5 shadow-sm ${appearance.edge}`}
      >
        <div className="flex min-w-0 items-start gap-2">
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold tabular-nums text-foreground">
              {appointmentTimeLabel(item)}
            </p>
            <a
              href={`${basePath}/candidates/${item.candidate_id}?tab=evaluations&origin=schedule`}
              onClick={() => rememberRecruitmentReturn("schedule")}
              className="mt-1 block break-words rounded-sm text-[13px] font-semibold leading-snug hover:text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
            >
              {candidateName}
            </a>
            <p className="mt-0.5 break-words text-[11px] text-muted-foreground">
              {item.subject || "Subject not set"}
            </p>
          </div>
          {actions.length ? (
            <ActionMenu
              items={actions}
              label={`Actions for ${candidateName}`}
            />
          ) : null}
        </div>
        <p className="mt-2 text-xs font-semibold">{appointmentTitle(item)}</p>
        <p className="mt-1 break-words text-[11px] leading-4 text-muted-foreground">
          {evaluatorLabel}
          {item.appointment_format ? ` · ${item.appointment_format}` : ""}
        </p>
        {item.topic ? (
          <p className="mt-1 break-words text-[11px] leading-4 text-muted-foreground">
            Topic: {item.topic}
          </p>
        ) : null}
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <span
            className={`inline-flex min-h-7 items-center gap-1 rounded-full border px-2 py-1 text-[9px] font-bold uppercase tracking-wide ${appearance.badge}`}
          >
            <StatusIcon className="h-3 w-3" />
            {appearance.label}
          </span>
          {sessionLabel ? (
            <button
              type="button"
              onClick={() => onSession(item)}
              className="ml-auto inline-flex min-h-11 items-center justify-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground transition-colors duration-150 hover:bg-primary/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 motion-reduce:transition-none"
            >
              <Play className="h-3.5 w-3.5" />
              {sessionLabel}
            </button>
          ) : null}
        </div>
      </article>
    );
  }

  return (
    <article
      className={`min-w-0 rounded-xl border border-l-4 border-border bg-card p-3 shadow-sm transition-colors duration-150 hover:bg-muted/20 motion-reduce:transition-none ${appearance.edge}`}
    >
      <div className="grid min-w-0 gap-3 lg:grid-cols-[6.5rem_minmax(11rem,1.2fr)_minmax(10rem,.8fr)_minmax(12rem,1fr)_auto] lg:items-center">
        <div className="flex items-start gap-2 lg:block">
          <Clock3 className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground lg:hidden" />
          <div>
            {showDate ? (
              <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                {shortDateLabel(
                  schoolDateKeyFromValue(item.starts_at) || schoolDateKey(),
                )}
              </p>
            ) : null}
            <p className="text-sm font-bold tabular-nums text-foreground">
              {appointmentTimeLabel(item)}
            </p>
          </div>
        </div>

        <div className="min-w-0">
          <a
            href={`${basePath}/candidates/${item.candidate_id}?tab=evaluations&origin=schedule`}
            onClick={() => rememberRecruitmentReturn("schedule")}
            className="block break-words rounded-sm text-sm font-semibold leading-snug hover:text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
          >
            {candidateName}
          </a>
          <p className="mt-0.5 break-words text-xs text-muted-foreground">
            {item.subject || "Subject not set"}
          </p>
        </div>

        <div className="min-w-0">
          <p className="text-xs font-semibold text-foreground">
            {appointmentTitle(item)}
          </p>
          {item.topic ? (
            <p className="mt-0.5 break-words text-[11px] text-muted-foreground">
              Topic: {item.topic}
            </p>
          ) : null}
        </div>

        <div className="min-w-0 text-xs text-muted-foreground">
          <p className="break-words">{evaluatorLabel}</p>
          <div className="mt-0.5 flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-[11px]">
            {item.appointment_format ? (
              <span>{item.appointment_format}</span>
            ) : null}
            {item.location_or_link ? (
              externalLocation ? (
                <a
                  href={item.location_or_link}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 font-semibold text-primary hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
                >
                  Open meeting
                  <ExternalLink className="h-3 w-3" />
                </a>
              ) : (
                <span className="break-words">{item.location_or_link}</span>
              )
            ) : null}
          </div>
        </div>

        <div className="flex min-w-0 flex-wrap items-center gap-2 lg:justify-end">
          <span
            className={`inline-flex min-h-8 items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide ${appearance.badge}`}
          >
            <StatusIcon className="h-3.5 w-3.5" />
            {appearance.label}
          </span>
          {sessionLabel ? (
            <button
              type="button"
              onClick={() => onSession(item)}
              className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground transition-colors duration-150 hover:bg-primary/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 motion-reduce:transition-none"
            >
              <Play className="h-4 w-4" />
              {sessionLabel}
            </button>
          ) : null}
          {actions.length ? (
            <ActionMenu
              items={actions}
              label={`Actions for ${candidateName}`}
            />
          ) : null}
        </div>
      </div>
    </article>
  );
}

export function ScheduleView({
  basePath,
  role,
  options,
  onAnnouncement,
}: {
  basePath: string;
  role: RecruitmentRole;
  options?: RecruitmentOptions;
  onAnnouncement: (message: string, tone?: FloatingToastTone) => void;
}) {
  const queryClient = useQueryClient();
  const initial = useMemo(() => new URLSearchParams(window.location.search), []);
  const initialHistoryStatus = initial.get("status") || "";
  const [mode, setMode] = useState<ScheduleMode>(
    initial.get("mode") === "week" ? "week" : "day",
  );
  const [section, setSection] = useState<ScheduleSection>(
    initial.get("schedule_section") === "history" ? "history" : "queue",
  );
  const [anchor, setAnchor] = useState(
    () => schoolDateKeyFromValue(initial.get("date")) || schoolDateKey(),
  );
  const [filters, setFilters] = useState<ScheduleFilters>({
    appointmentType: initial.get("appointment_type") || "",
    staffId: initial.get("responsible_account_id") || "",
    historyStatus: historyStatuses.has(initialHistoryStatus as HistoryStatus)
      ? (initialHistoryStatus as HistoryStatus)
      : "",
  });
  const [draftFilters, setDraftFilters] = useState(filters);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [overdueOpen, setOverdueOpen] = useState(false);
  const [editing, setEditing] =
    useState<RecruitmentAppointment | null>(null);
  const [sessionSelection, setSessionSelection] =
    useState<RecruitmentAppointment | null>(null);
  const [statusAction, setStatusAction] = useState<{
    item: RecruitmentAppointment;
    status: "cancelled" | "no_show";
  } | null>(null);

  const fullWeekBounds = schoolWeekBounds(new Date(`${anchor}T12:00:00Z`));
  const bounds =
    mode === "week"
      ? {
          start: fullWeekBounds.start,
          end: addDaysToDateKey(fullWeekBounds.start, 5),
        }
      : { start: anchor, end: anchor };
  const rangeEnd = addDaysToDateKey(bounds.end, 1);
  const selectedStatus =
    section === "queue"
      ? queueStatusFilter
      : filters.historyStatus || historyStatusFilter;
  const mainQuery = buildAppointmentQuery({
    start: bounds.start,
    end: rangeEnd,
    status: selectedStatus,
    filters,
  });
  const overdueQuery = buildAppointmentQuery({
    status: "overdue",
    filters,
  });

  const appointments = useQuery({
    queryKey: [
      "recruitment",
      "appointments",
      "schedule",
      section,
      mode,
      bounds.start,
      bounds.end,
      selectedStatus,
      filters.appointmentType,
      filters.staffId,
    ],
    queryFn: () =>
      recruitmentRequest<AppointmentData>(
        `${RECRUITMENT_API}/appointments?${mainQuery}`,
      ),
    placeholderData: keepPreviousData,
  });
  const overdueAppointments = useQuery({
    queryKey: [
      "recruitment",
      "appointments",
      "schedule-overdue",
      filters.appointmentType,
      filters.staffId,
    ],
    queryFn: () =>
      recruitmentRequest<AppointmentData>(
        `${RECRUITMENT_API}/appointments?${overdueQuery}`,
      ),
    placeholderData: keepPreviousData,
    enabled: section === "queue",
  });
  const sessionCandidate = useQuery({
    queryKey: [
      "recruitment",
      "candidate",
      sessionSelection?.candidate_id,
    ],
    queryFn: () =>
      recruitmentRequest<RecruitmentCandidate>(
        `${RECRUITMENT_API}/candidates/${sessionSelection?.candidate_id}`,
      ),
    enabled: Boolean(sessionSelection),
  });
  const mutation = useMutation({
    mutationFn: ({
      url,
      method = "POST",
      values,
    }: {
      url: string;
      method?: string;
      values: unknown;
    }) =>
      recruitmentRequest<MutationPayload>(url, {
        method,
        body: jsonBody(values),
      }),
    onSuccess: (result) => {
      onAnnouncement(result.message || "Appointment updated.");
      setEditing(null);
      setStatusAction(null);
      void queryClient.invalidateQueries({ queryKey: ["recruitment"] });
    },
    onError: (error) => onAnnouncement(queryError(error), "error"),
  });

  useEffect(() => {
    replaceUrlParams({
      mode: mode === "day" ? "" : mode,
      schedule_section: section === "queue" ? "" : section,
      date: anchor === schoolDateKey() ? "" : anchor,
      appointment_type: filters.appointmentType,
      status:
        section === "history" && filters.historyStatus
          ? filters.historyStatus
          : "",
      responsible_account_id: filters.staffId,
    });
  }, [anchor, filters, mode, section]);
  useEffect(() => {
    if (appointments.data) restoreRecruitmentReturn("schedule");
  }, [appointments.data]);

  const weekDays = useMemo(
    () =>
      Array.from({ length: 6 }, (_, index) =>
        addDaysToDateKey(bounds.start, index),
      ),
    [bounds.start],
  );
  const visibleItems = useMemo(
    () =>
      [...(appointments.data?.items || [])].sort((left, right) =>
        appointmentSort(section, left, right),
      ),
    [appointments.data?.items, section],
  );
  const overdueItems = useMemo(
    () =>
      [...(overdueAppointments.data?.items || [])].sort(
        (left, right) =>
          new Date(left.starts_at).getTime() -
          new Date(right.starts_at).getTime(),
      ),
    [overdueAppointments.data?.items],
  );
  const itemsForDay = (date: string) =>
    visibleItems.filter(
      (item) => schoolDateKeyFromValue(item.starts_at) === date,
    );
  const canManage = role === "hr_manager" || role === "ceo";
  const moveRange = (direction: -1 | 1) =>
    setAnchor(addDaysToDateKey(anchor, direction * (mode === "week" ? 7 : 1)));
  const updateStatus = (
    value: RecruitmentAppointment,
    nextStatus: "cancelled" | "no_show",
  ) => setStatusAction({ item: value, status: nextStatus });
  const submitEdit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editing) return;
    mutation.mutate({
      url: `${RECRUITMENT_API}/candidates/${editing.candidate_id}/appointments/${editing.id}`,
      method: "PATCH",
      values: {
        ...formValues(event.currentTarget),
        expected_version: editing.version,
      },
    });
  };

  const openFilters = () => {
    setDraftFilters(filters);
    setFiltersOpen(true);
  };
  const clearFilters = () => {
    const cleared: ScheduleFilters = {
      appointmentType: "",
      staffId: "",
      historyStatus: "",
    };
    setFilters(cleared);
    setDraftFilters(cleared);
  };
  const staffName = (id: string) =>
    options?.staff.find((person) => String(person.id) === id)?.name || "Staff";
  const activeFilters = [
    filters.appointmentType
      ? {
          key: "appointmentType" as const,
          label:
            filters.appointmentType === "job_interview"
              ? "Job Interviews"
              : "Demo Lessons",
        }
      : null,
    filters.staffId
      ? { key: "staffId" as const, label: staffName(filters.staffId) }
      : null,
    section === "history" && filters.historyStatus
      ? {
          key: "historyStatus" as const,
          label: statusPresentation[filters.historyStatus].label,
        }
      : null,
  ].filter(Boolean) as Array<{
    key: keyof ScheduleFilters;
    label: string;
  }>;
  const navigationLabel =
    mode === "day"
      ? `${anchor === schoolDateKey() ? "Today" : scheduleDayLabel(anchor).split(",")[0]} · ${shortDateLabel(anchor)}`
      : `${schoolDateKey() >= bounds.start && schoolDateKey() <= bounds.end ? "This week · " : ""}${shortDateLabel(bounds.start)}–${shortDateLabel(bounds.end)}`;

  const appointmentRowProps = {
    basePath,
    canManage,
    onEdit: setEditing,
    onSession: setSessionSelection,
    onStatus: updateStatus,
  };

  const body = appointments.error && !appointments.data ? (
    <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-500/40 dark:bg-red-950/20 dark:text-red-200">
      {queryError(appointments.error)}
    </div>
  ) : appointments.isLoading && !appointments.data ? (
    <div className="h-56 animate-pulse rounded-xl border border-border bg-muted/40 motion-reduce:animate-none" />
  ) : mode === "day" ? (
    <section className="overflow-hidden rounded-xl border border-border bg-card">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-muted/35 px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold">{scheduleDateLabel(anchor)}</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {section === "queue"
              ? "Appointments that still need action"
              : "Recorded outcomes and appointments not conducted"}
          </p>
        </div>
        <span className="rounded-full border border-border bg-card px-2.5 py-1 text-xs font-semibold tabular-nums text-muted-foreground">
          {visibleItems.length} {visibleItems.length === 1 ? "appointment" : "appointments"}
        </span>
      </header>
      <div className="space-y-2 p-2 sm:p-3">
        {visibleItems.map((item) => (
          <AppointmentRow
            key={item.id}
            item={item}
            {...appointmentRowProps}
          />
        ))}
        {!visibleItems.length ? (
          <div className="rounded-lg border border-dashed border-border px-4 py-10 text-center">
            <p className="text-sm font-semibold">
              {section === "queue"
                ? "No remaining appointments for this day"
                : "No history for this day"}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {section === "queue"
                ? "Recorded results are kept separately so active work stays clear."
                : "Try another date or clear the active filters."}
            </p>
            {section === "queue" ? (
              <button
                type="button"
                onClick={() => setSection("history")}
                className="mt-3 inline-flex min-h-11 items-center gap-2 rounded-lg px-3 text-xs font-semibold text-primary hover:bg-primary/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
              >
                <History className="h-4 w-4" />
                View this day&apos;s history
              </button>
            ) : null}
          </div>
        ) : null}
      </div>
    </section>
  ) : (
    <section className="grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-6">
      {weekDays.map((day) => {
        const dayItems = itemsForDay(day);
        const isToday = day === schoolDateKey();
        return (
          <div
            key={day}
            className="min-w-0 overflow-hidden rounded-xl border border-border bg-card xl:h-[min(62vh,42rem)] xl:overflow-y-auto"
          >
            <div
              className={`sticky top-0 z-10 flex items-center justify-between gap-2 border-b border-border px-3 py-2.5 text-xs font-semibold shadow-sm ${
                isToday
                  ? "bg-primary/10 text-primary"
                  : "bg-muted text-foreground"
              }`}
            >
              <span>{scheduleDayLabel(day)}</span>
              <span className="rounded-full bg-card px-2 py-0.5 text-[10px] tabular-nums text-muted-foreground">
                {dayItems.length}
              </span>
            </div>
            <div className="space-y-2 p-2">
              {dayItems.map((item) => (
                <AppointmentRow
                  key={item.id}
                  item={item}
                  compact
                  {...appointmentRowProps}
                />
              ))}
              {!dayItems.length ? (
                <p className="rounded-lg border border-dashed border-border px-2 py-6 text-center text-[11px] text-muted-foreground">
                  No appointments
                </p>
              ) : null}
            </div>
          </div>
        );
      })}
    </section>
  );

  return (
    <div className="min-w-0 space-y-3 overflow-x-clip">
      <section className="rounded-xl border border-border bg-card p-3">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <div className="inline-flex min-h-11 rounded-lg border border-border bg-muted/40 p-1">
              <button
                type="button"
                onClick={() => setSection("queue")}
                aria-pressed={section === "queue"}
                className={`inline-flex min-h-11 items-center gap-1.5 rounded-md px-3 text-xs font-semibold transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 motion-reduce:transition-none ${
                  section === "queue"
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <List className="h-4 w-4" />
                Work Queue
              </button>
              <button
                type="button"
                onClick={() => setSection("history")}
                aria-pressed={section === "history"}
                className={`inline-flex min-h-11 items-center gap-1.5 rounded-md px-3 text-xs font-semibold transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 motion-reduce:transition-none ${
                  section === "history"
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <History className="h-4 w-4" />
                History
              </button>
            </div>

            <div className="inline-flex min-h-11 rounded-lg border border-border bg-muted/40 p-1">
              <button
                type="button"
                onClick={() => setMode("day")}
                aria-pressed={mode === "day"}
                className={`inline-flex min-h-11 items-center gap-1.5 rounded-md px-3 text-xs font-semibold transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 motion-reduce:transition-none ${
                  mode === "day"
                    ? "bg-card text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <List className="h-4 w-4" />
                Day
              </button>
              <button
                type="button"
                onClick={() => setMode("week")}
                aria-pressed={mode === "week"}
                className={`inline-flex min-h-11 items-center gap-1.5 rounded-md px-3 text-xs font-semibold transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 motion-reduce:transition-none ${
                  mode === "week"
                    ? "bg-card text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <CalendarDays className="h-4 w-4" />
                Week
              </button>
            </div>
          </div>

          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <div className="flex min-w-0 flex-1 items-center sm:flex-none">
              <button
                type="button"
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-l-lg border border-border transition-colors duration-150 hover:bg-muted focus:outline-none focus-visible:z-10 focus-visible:ring-2 focus-visible:ring-primary/30 motion-reduce:transition-none"
                onClick={() => moveRange(-1)}
                aria-label={`Previous ${mode === "week" ? "week" : "day"}`}
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <label className="relative flex min-h-11 min-w-0 flex-1 cursor-pointer items-center justify-center border-y border-border px-3 text-center text-xs font-semibold focus-within:z-10 focus-within:ring-2 focus-within:ring-primary/30 sm:min-w-44">
                <span className="pointer-events-none truncate">{navigationLabel}</span>
                <input
                  type="date"
                  aria-label="Choose schedule date"
                  value={anchor}
                  onChange={(event) => {
                    if (event.target.value) setAnchor(event.target.value);
                  }}
                  className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
                />
              </label>
              <button
                type="button"
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-r-lg border border-border transition-colors duration-150 hover:bg-muted focus:outline-none focus-visible:z-10 focus-visible:ring-2 focus-visible:ring-primary/30 motion-reduce:transition-none"
                onClick={() => moveRange(1)}
                aria-label={`Next ${mode === "week" ? "week" : "day"}`}
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
            {anchor !== schoolDateKey() ? (
              <button
                type="button"
                onClick={() => setAnchor(schoolDateKey())}
                className="min-h-11 rounded-lg px-3 text-xs font-semibold text-primary transition-colors duration-150 hover:bg-primary/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 motion-reduce:transition-none"
              >
                Today
              </button>
            ) : null}
            <button
              type="button"
              className={`${secondaryButtonClass} relative !min-h-11`}
              onClick={openFilters}
              aria-label={`Filters${activeFilters.length ? `, ${activeFilters.length} active` : ""}`}
            >
              <Filter className="h-4 w-4" />
              Filters
              {activeFilters.length ? (
                <span className="rounded-full bg-primary px-1.5 py-0.5 text-[9px] font-bold text-primary-foreground">
                  {activeFilters.length}
                </span>
              ) : null}
            </button>
          </div>
        </div>

        <div className="mt-2 flex min-w-0 flex-wrap items-center gap-2">
          <span className="text-[11px] font-medium text-muted-foreground">
            Asia/Tashkent
          </span>
          {activeFilters.map((filter) => (
            <button
              key={filter.key}
              type="button"
              onClick={() =>
                setFilters((current) => ({
                  ...current,
                  [filter.key]: "",
                }))
              }
              aria-label={`Remove ${filter.label} filter`}
              className="inline-flex min-h-11 items-center gap-1 rounded-full border border-border bg-muted/50 px-2.5 text-[11px] font-semibold text-foreground transition-colors duration-150 hover:border-primary/40 hover:text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 motion-reduce:transition-none"
            >
              {filter.label}
              <X className="h-3 w-3" />
            </button>
          ))}
          {activeFilters.length ? (
            <button
              type="button"
              onClick={clearFilters}
              className="min-h-11 px-2 text-[11px] font-semibold text-primary hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
            >
              Clear all
            </button>
          ) : null}
        </div>
      </section>

      {section === "queue" && overdueAppointments.error ? (
        <div className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-500/40 dark:bg-amber-950/20 dark:text-amber-100">
          Overdue appointments could not be loaded. {queryError(overdueAppointments.error)}
        </div>
      ) : null}

      {section === "queue" && overdueItems.length ? (
        <section className="overflow-hidden rounded-xl border border-amber-300 bg-amber-50/70 dark:border-amber-500/40 dark:bg-amber-950/20">
          <button
            type="button"
            className="flex min-h-12 w-full items-center gap-3 px-4 py-3 text-left transition-colors duration-150 hover:bg-amber-100/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-amber-500 motion-reduce:transition-none dark:hover:bg-amber-900/20"
            onClick={() => setOverdueOpen((current) => !current)}
            aria-expanded={overdueOpen}
            aria-controls="overdue-appointments"
          >
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-100">
              <AlertTriangle className="h-4 w-4" />
            </span>
            <span className="min-w-0 flex-1">
              <strong className="block text-sm text-amber-950 dark:text-amber-50">
                {overdueItems.length} overdue {overdueItems.length === 1 ? "appointment" : "appointments"}
              </strong>
              <span className="block text-xs text-amber-800 dark:text-amber-200">
                Scheduled time passed without the session starting
              </span>
            </span>
            <ChevronDown
              className={`h-4 w-4 shrink-0 text-amber-800 transition-transform duration-200 motion-reduce:transition-none dark:text-amber-200 ${
                overdueOpen ? "rotate-180" : ""
              }`}
            />
          </button>
          {overdueOpen ? (
            <div
              id="overdue-appointments"
              className="max-h-[28rem] space-y-2 overflow-y-auto border-t border-amber-300/70 bg-card/70 p-2 sm:p-3 dark:border-amber-500/30"
            >
              {overdueItems.map((item) => (
                <AppointmentRow
                  key={item.id}
                  item={item}
                  showDate
                  {...appointmentRowProps}
                />
              ))}
            </div>
          ) : null}
        </section>
      ) : null}

      <div
        aria-busy={appointments.isFetching}
        className={`transition-[opacity,transform] duration-200 ease-out motion-reduce:transition-none ${
          appointments.isFetching
            ? "translate-y-0.5 opacity-65 motion-reduce:translate-y-0"
            : "translate-y-0 opacity-100"
        }`}
      >
        {body}
      </div>

      <Drawer
        open={filtersOpen}
        onClose={() => setFiltersOpen(false)}
        title="Schedule filters"
        description="Narrow the current work queue or history without changing the selected date."
        footer={
          <div className="flex flex-wrap justify-end gap-2">
            <button
              type="button"
              className={`${secondaryButtonClass} !min-h-11`}
              onClick={() =>
                setDraftFilters({
                  appointmentType: "",
                  staffId: "",
                  historyStatus: "",
                })
              }
            >
              Clear
            </button>
            <button
              type="button"
              className={`${buttonClass} !min-h-11`}
              onClick={() => {
                setFilters(draftFilters);
                setFiltersOpen(false);
              }}
            >
              Apply filters
            </button>
          </div>
        }
      >
        <div className="grid gap-4">
          <label className="text-xs font-semibold">
            Appointment type
            <select
              className={`${fieldClass} mt-1 !min-h-11`}
              value={draftFilters.appointmentType}
              onChange={(event) =>
                setDraftFilters((current) => ({
                  ...current,
                  appointmentType: event.target.value,
                }))
              }
            >
              <option value="">All types</option>
              <option value="job_interview">Job Interviews</option>
              <option value="demo_lesson">Demo Lessons</option>
            </select>
          </label>
          <label className="text-xs font-semibold">
            Responsible staff
            <select
              className={`${fieldClass} mt-1 !min-h-11`}
              value={draftFilters.staffId}
              onChange={(event) =>
                setDraftFilters((current) => ({
                  ...current,
                  staffId: event.target.value,
                }))
              }
            >
              <option value="">All staff</option>
              {options?.staff.map((person) => (
                <option key={person.id} value={person.id}>
                  {person.name}
                </option>
              ))}
            </select>
          </label>
          {section === "history" ? (
            <label className="text-xs font-semibold">
              Result
              <select
                className={`${fieldClass} mt-1 !min-h-11`}
                value={draftFilters.historyStatus}
                onChange={(event) =>
                  setDraftFilters((current) => ({
                    ...current,
                    historyStatus: event.target.value as HistoryStatus,
                  }))
                }
              >
                <option value="">All results</option>
                <option value="passed">Passed</option>
                <option value="failed">Failed</option>
                <option value="not_conducted">Not Conducted</option>
              </select>
            </label>
          ) : null}
        </div>
      </Drawer>

      <Drawer
        open={Boolean(editing)}
        onClose={() => {
          if (!mutation.isPending) setEditing(null);
        }}
        title="Reschedule appointment"
        description={editing?.candidate_name}
        footer={
          <div className="flex justify-end gap-2">
            <button
              type="button"
              className={`${secondaryButtonClass} !min-h-11`}
              onClick={() => setEditing(null)}
              disabled={mutation.isPending}
            >
              Cancel
            </button>
            <button
              type="submit"
              form="schedule-edit-form"
              className={`${buttonClass} !min-h-11`}
              disabled={mutation.isPending}
            >
              {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Save appointment
            </button>
          </div>
        }
      >
        {editing ? (
          <form id="schedule-edit-form" onSubmit={submitEdit}>
            <AppointmentForm
              appointmentType={editing.appointment_type}
              appointment={editing}
              options={options}
            />
          </form>
        ) : null}
      </Drawer>

      {sessionSelection && !sessionCandidate.data ? (
        <Modal
          open
          onClose={() => {
            if (!sessionCandidate.isFetching) setSessionSelection(null);
          }}
          title={sessionSelection.can_resume ? "Resume appointment" : "Open appointment"}
          subtitle={sessionSelection.candidate_name}
          size="sm"
        >
          <ModalBody>
            {sessionCandidate.error ? (
              <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-500/40 dark:bg-red-950/20 dark:text-red-200">
                <p>{queryError(sessionCandidate.error)}</p>
                <button
                  type="button"
                  onClick={() => void sessionCandidate.refetch()}
                  className="mt-3 min-h-11 rounded-lg px-3 font-semibold text-primary hover:bg-primary/5"
                >
                  Try again
                </button>
              </div>
            ) : (
              <div className="flex min-h-28 items-center justify-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-5 w-5 animate-spin motion-reduce:animate-none" />
                Loading candidate details…
              </div>
            )}
          </ModalBody>
        </Modal>
      ) : null}

      {sessionSelection && sessionCandidate.data ? (
        sessionSelection.appointment_type === "job_interview" ? (
          <InterviewSessionModal
            candidate={sessionCandidate.data}
            appointment={sessionSelection}
            options={options}
            open
            onClose={() => setSessionSelection(null)}
            onAnnouncement={onAnnouncement}
          />
        ) : (
          <DemoSessionModal
            candidate={sessionCandidate.data}
            appointment={sessionSelection}
            open
            onClose={() => setSessionSelection(null)}
            onAnnouncement={onAnnouncement}
          />
        )
      ) : null}

      <Modal
        open={Boolean(statusAction)}
        onClose={() => {
          if (!mutation.isPending) setStatusAction(null);
        }}
        title={
          statusAction?.status === "cancelled"
            ? "Cancel appointment"
            : "Mark no-show"
        }
        subtitle={statusAction?.item.candidate_name}
        size="sm"
      >
        {statusAction ? (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              const values = formValues(event.currentTarget);
              mutation.mutate({
                url: `${RECRUITMENT_API}/candidates/${statusAction.item.candidate_id}/appointments/${statusAction.item.id}/${
                  statusAction.status === "cancelled" ? "cancel" : "no-show"
                }`,
                values: {
                  expected_version: statusAction.item.version,
                  reason: values.reason,
                },
              });
            }}
          >
            <ModalBody>
              <label className="text-xs font-semibold">
                Reason / note
                <textarea
                  autoFocus
                  required={statusAction.status === "cancelled"}
                  name="reason"
                  className={`${fieldClass} mt-1 min-h-24`}
                />
              </label>
            </ModalBody>
            <ModalFooter>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  className={`${secondaryButtonClass} !min-h-11`}
                  onClick={() => setStatusAction(null)}
                  disabled={mutation.isPending}
                >
                  Back
                </button>
                <button
                  type="submit"
                  className={`${buttonClass} !min-h-11`}
                  disabled={mutation.isPending}
                >
                  {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                  {statusAction.status === "cancelled"
                    ? "Cancel appointment"
                    : "Mark no-show"}
                </button>
              </div>
            </ModalFooter>
          </form>
        ) : null}
      </Modal>
    </div>
  );
}
