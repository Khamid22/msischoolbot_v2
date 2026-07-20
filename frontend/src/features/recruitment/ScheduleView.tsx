import {
  Ban,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  List,
  Pencil,
  UserX,
} from "lucide-react";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useEffect, useMemo, useState, type FormEvent } from "react";

import { AppointmentForm } from "@/features/recruitment/AppointmentForm";
import {
  formValues,
  jsonBody,
  recruitmentRequest,
} from "@/features/recruitment/api";
import {
  dateLabel,
  type RecruitmentAppointment,
  type RecruitmentOptions,
  type RecruitmentRole,
} from "@/features/recruitment/model";
import {
  RECRUITMENT_API,
  EmptyLine,
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

type ScheduleMode = "agenda" | "week";
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

const scheduleDayFormatter = new Intl.DateTimeFormat("en", {
  weekday: "short",
  month: "short",
  day: "numeric",
  timeZone: "Asia/Tashkent",
});
const scheduleDateFormatter = new Intl.DateTimeFormat("en", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "Asia/Tashkent",
});
const scheduleTimeFormatter = new Intl.DateTimeFormat("en", {
  hour: "numeric",
  minute: "2-digit",
  timeZone: "Asia/Tashkent",
});

const statusPresentation: Record<
  DisplayStatus,
  { label: string; card: string; badge: string }
> = {
  passed: {
    label: "Passed",
    card:
      "border-emerald-300 bg-emerald-50/70 dark:border-emerald-500/40 dark:bg-emerald-950/20",
    badge: "bg-emerald-100 text-emerald-800",
  },
  failed: {
    label: "Failed",
    card:
      "border-red-300 bg-red-50/70 dark:border-red-500/40 dark:bg-red-950/20",
    badge: "bg-red-100 text-red-800",
  },
  scheduled: {
    label: "Scheduled",
    card:
      "border-blue-300 bg-blue-50/70 dark:border-blue-500/40 dark:bg-blue-950/20",
    badge: "bg-blue-100 text-blue-800",
  },
  in_progress: {
    label: "In Progress",
    card:
      "border-violet-300 bg-violet-50/70 dark:border-violet-500/40 dark:bg-violet-950/20",
    badge: "bg-violet-100 text-violet-800",
  },
  overdue: {
    label: "Overdue",
    card:
      "border-amber-300 bg-amber-50/70 dark:border-amber-500/40 dark:bg-amber-950/20",
    badge: "bg-amber-100 text-amber-900",
  },
  not_conducted: {
    label: "Not Conducted",
    card: "border-border bg-muted/40",
    badge: "bg-slate-200 text-slate-700",
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

function appointmentTimeLabel(item: RecruitmentAppointment) {
  const startsAt = new Date(item.starts_at);
  return Number.isNaN(startsAt.getTime())
    ? "Time not set"
    : scheduleTimeFormatter.format(startsAt);
}

function appointmentTitle(item: RecruitmentAppointment) {
  return item.appointment_type === "job_interview"
    ? "Job interview"
    : "Demo lesson";
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

function AppointmentCard({
  item,
  basePath,
  canManage,
  compact = false,
  onEdit,
  onStatus,
}: {
  item: RecruitmentAppointment;
  basePath: string;
  canManage: boolean;
  compact?: boolean;
  onEdit: (item: RecruitmentAppointment) => void;
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
  const evaluatorLabel =
    item.appointment_type === "demo_lesson"
      ? item.evaluated_by_name ||
        item.responsible_name ||
        "Evaluator not assigned"
      : item.responsible_name || "HR not assigned";

  return (
    <article
      className={`min-w-0 rounded-lg border shadow-sm ${appearance.card} ${
        compact ? "p-2" : "p-3"
      }`}
    >
      <div className="flex min-w-0 items-start gap-1.5">
        <a
          href={`${basePath}/candidates/${item.candidate_id}?tab=evaluations&origin=schedule`}
          onClick={() => rememberRecruitmentReturn("schedule")}
          className="min-w-0 flex-1 rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
        >
          <p
            className={`${compact ? "text-[13px]" : "text-sm"} break-words font-semibold leading-snug hover:text-primary`}
          >
            {candidateName}
          </p>
          {!compact ? (
            <p className="mt-0.5 break-words text-xs font-medium text-muted-foreground">
              {appointmentTitle(item)} · {dateLabel(item.starts_at)}
            </p>
          ) : null}
        </a>
        {actions.length ? (
          <ActionMenu
            items={actions}
            label={`Actions for ${candidateName}`}
          />
        ) : null}
      </div>
      {compact ? (
        <p className="mt-1 break-words text-xs font-medium text-muted-foreground">
          {appointmentTitle(item)}
        </p>
      ) : null}
      <p
        className={`${compact ? "mt-1 text-[13px]" : "mt-2 text-xs"} font-semibold tabular-nums text-foreground`}
      >
        {appointmentTimeLabel(item)}
      </p>
      <div className="mt-2 flex min-w-0 flex-wrap items-center gap-1.5">
        <span className="min-w-0 flex-1 break-words text-[11px] text-muted-foreground">
          {evaluatorLabel}
        </span>
        <span
          className={`shrink-0 rounded-full px-2 py-1 text-[9px] font-bold uppercase tracking-wide ${appearance.badge}`}
        >
          {appearance.label}
        </span>
      </div>
      <div className="mt-1 flex flex-wrap gap-x-2 gap-y-0.5 text-[11px] text-muted-foreground">
        {item.appointment_format ? (
          <span className="break-words">{item.appointment_format}</span>
        ) : null}
        {item.location_or_link ? (
          <span className="max-w-full break-all">{item.location_or_link}</span>
        ) : null}
        {item.topic ? (
          <span className="break-words">Topic: {item.topic}</span>
        ) : null}
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
  const initial = new URLSearchParams(window.location.search);
  const [mode, setMode] = useState<ScheduleMode>(
    initial.get("mode") === "week" ? "week" : "agenda",
  );
  const [anchor, setAnchor] = useState(
    () => schoolDateKeyFromValue(initial.get("date")) || schoolDateKey(),
  );
  const [type, setType] = useState(
    initial.get("appointment_type") || "",
  );
  const [status, setStatus] = useState(initial.get("status") || "");
  const [staffId, setStaffId] = useState(
    initial.get("responsible_account_id") || "",
  );
  const [editing, setEditing] =
    useState<RecruitmentAppointment | null>(null);
  const [statusAction, setStatusAction] = useState<{
    item: RecruitmentAppointment;
    status: "cancelled" | "no_show";
  } | null>(null);
  const bounds =
    mode === "week"
      ? schoolWeekBounds(new Date(`${anchor}T12:00:00Z`))
      : { start: anchor, end: addDaysToDateKey(anchor, 29) };
  const rangeEnd = addDaysToDateKey(bounds.end, 1);
  const query = new URLSearchParams({
    page: "1",
    per_page: "500",
    from: schoolDayStartIso(bounds.start),
    to: schoolDayStartIso(rangeEnd),
  });
  if (type) query.set("appointment_type", type);
  if (status) query.set("status", status);
  if (staffId) query.set("responsible_account_id", staffId);

  const appointments = useQuery({
    queryKey: [
      "recruitment",
      "appointments",
      bounds.start,
      bounds.end,
      type,
      status,
      staffId,
    ],
    queryFn: () =>
      recruitmentRequest<AppointmentData>(
        `${RECRUITMENT_API}/appointments?${query}`,
      ),
    placeholderData: keepPreviousData,
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
      mode: mode === "agenda" ? "" : mode,
      date: anchor === schoolDateKey() ? "" : anchor,
      appointment_type: type,
      status,
      responsible_account_id: staffId,
    });
  }, [anchor, mode, staffId, status, type]);
  useEffect(() => {
    if (appointments.data) restoreRecruitmentReturn("schedule");
  }, [appointments.data]);

  const weekDays = useMemo(
    () =>
      Array.from({ length: 7 }, (_, index) =>
        addDaysToDateKey(bounds.start, index),
      ),
    [bounds.start],
  );
  const visibleItems = appointments.data?.items || [];
  const itemsForDay = (date: string) =>
    visibleItems.filter(
      (item) => schoolDateKeyFromValue(item.starts_at) === date,
    );
  const canManage = role === "hr_manager" || role === "ceo";
  const moveRange = (direction: -1 | 1) =>
    setAnchor(
      addDaysToDateKey(anchor, direction * (mode === "week" ? 7 : 30)),
    );
  const editAppointment = (value: RecruitmentAppointment) => {
    setEditing(value);
  };
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

  const body = appointments.error && !appointments.data ? (
    <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
      {queryError(appointments.error)}
    </div>
  ) : appointments.isLoading && !appointments.data ? (
    <div className="h-56 animate-pulse rounded-xl border border-border bg-muted/40 motion-reduce:animate-none" />
  ) : mode === "agenda" ? (
    <div className="space-y-2">
      {visibleItems.map((item) => (
        <AppointmentCard
          key={item.id}
          item={item}
          basePath={basePath}
          canManage={canManage}
          onEdit={editAppointment}
          onStatus={updateStatus}
        />
      ))}
      {!visibleItems.length ? (
        <EmptyLine>No appointments in this period.</EmptyLine>
      ) : null}
    </div>
  ) : (
    <div className="max-w-full overflow-x-auto rounded-xl border border-border bg-card">
      <section className="grid min-w-[84rem] grid-cols-7">
        {weekDays.map((day) => {
          const dayItems = itemsForDay(day);
          return (
            <div
              key={day}
              className="h-[min(62vh,42rem)] min-w-0 overflow-y-auto border-r border-border last:border-r-0"
            >
              <div className="sticky top-0 z-10 border-b border-border bg-muted px-2 py-2 text-center text-[11px] font-semibold uppercase tracking-wide shadow-sm">
                {scheduleDayLabel(day)}
              </div>
              <div className="space-y-2 p-2">
                {dayItems.map((item) => (
                  <AppointmentCard
                    key={item.id}
                    item={item}
                    basePath={basePath}
                    canManage={canManage}
                    compact
                    onEdit={editAppointment}
                    onStatus={updateStatus}
                  />
                ))}
                {!dayItems.length ? (
                  <p className="py-4 text-center text-[11px] text-muted-foreground">
                    No appointments
                  </p>
                ) : null}
              </div>
            </div>
          );
        })}
      </section>
    </div>
  );

  return (
    <div className="min-w-0 space-y-2 overflow-x-clip">
      <section className="rounded-xl border border-border bg-card p-3">
        <div className="flex flex-wrap items-end gap-2">
          <div className="inline-flex min-h-9 rounded-lg border border-border bg-muted/40 p-1">
            <button
              type="button"
              onClick={() => setMode("agenda")}
              aria-pressed={mode === "agenda"}
              className={`inline-flex min-h-9 items-center gap-1.5 rounded-md px-3 text-xs font-semibold ${
                mode === "agenda"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground"
              }`}
            >
              <List className="h-4 w-4" />
              Agenda
            </button>
            <button
              type="button"
              onClick={() => setMode("week")}
              aria-pressed={mode === "week"}
              className={`inline-flex min-h-9 items-center gap-1.5 rounded-md px-3 text-xs font-semibold ${
                mode === "week"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground"
              }`}
            >
              <CalendarDays className="h-4 w-4" />
              Week
            </button>
          </div>
          <div className="inline-flex min-h-9 items-center rounded-lg border border-border">
            <button
              type="button"
              className="flex h-9 w-9 items-center justify-center"
              onClick={() => moveRange(-1)}
              aria-label="Previous schedule period"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              type="button"
              className="min-h-9 border-x border-border px-3 text-xs font-semibold"
              onClick={() => setAnchor(schoolDateKey())}
            >
              Today
            </button>
            <button
              type="button"
              className="flex h-9 w-9 items-center justify-center"
              onClick={() => moveRange(1)}
              aria-label="Next schedule period"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
          <label className="min-w-36 flex-1 text-xs font-semibold text-muted-foreground">
            Type
            <select
              className={`${fieldClass} mt-1`}
              value={type}
              onChange={(event) => setType(event.target.value)}
            >
              <option value="">All types</option>
              <option value="job_interview">Job interviews</option>
              <option value="demo_lesson">Demo lessons</option>
            </select>
          </label>
          <label className="min-w-36 flex-1 text-xs font-semibold text-muted-foreground">
            Status
            <select
              className={`${fieldClass} mt-1`}
              value={status}
              onChange={(event) => setStatus(event.target.value)}
            >
              <option value="">All statuses</option>
              <option value="passed">Passed</option>
              <option value="failed">Failed</option>
              <option value="scheduled">Scheduled</option>
              <option value="in_progress">In Progress</option>
              <option value="overdue">Overdue</option>
              <option value="not_conducted">Not Conducted</option>
            </select>
          </label>
          <label className="min-w-44 flex-1 text-xs font-semibold text-muted-foreground">
            Staff
            <select
              className={`${fieldClass} mt-1`}
              value={staffId}
              onChange={(event) => setStaffId(event.target.value)}
            >
              <option value="">All staff</option>
              {options?.staff.map((person) => (
                <option key={person.id} value={person.id}>
                  {person.name}
                </option>
              ))}
            </select>
          </label>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          {scheduleDateLabel(bounds.start)} – {scheduleDateLabel(bounds.end)} ·
          Asia/Tashkent
        </p>
      </section>

      <div
        aria-busy={appointments.isFetching}
        className={`transition-opacity duration-200 motion-reduce:transition-none ${
          appointments.isFetching ? "opacity-65" : "opacity-100"
        }`}
      >
        {body}
      </div>

      <Drawer
        open={Boolean(editing)}
        onClose={() => {
          if (!mutation.isPending) {
            setEditing(null);
          }
        }}
        title="Reschedule appointment"
        description={editing?.candidate_name}
        footer={
          <div className="flex justify-end gap-2">
            <button
              type="button"
              className={secondaryButtonClass}
              onClick={() => setEditing(null)}
              disabled={mutation.isPending}
            >
              Cancel
            </button>
            <button
              type="submit"
              form="schedule-edit-form"
              className={buttonClass}
              disabled={mutation.isPending}
            >
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
                  className={secondaryButtonClass}
                  onClick={() => setStatusAction(null)}
                >
                  Back
                </button>
                <button type="submit" className={buttonClass}>
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
