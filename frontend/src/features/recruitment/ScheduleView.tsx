import { Ban, CalendarDays, ChevronLeft, ChevronRight, List, Pencil, UserX } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState, type FormEvent } from "react";

import { AppointmentForm } from "@/features/recruitment/AppointmentForm";
import { appointmentConflictDetails, formValues, jsonBody, recruitmentRequest } from "@/features/recruitment/api";
import { dateLabel, type RecruitmentAppointment, type RecruitmentOptions, type RecruitmentRole } from "@/features/recruitment/model";
import { RECRUITMENT_API, EmptyLine, PageState, buttonClass, fieldClass, queryError, rememberRecruitmentReturn, replaceUrlParams, restoreRecruitmentReturn, secondaryButtonClass } from "@/features/recruitment/ui";
import { addDaysToDateKey, schoolDateKey, schoolDateKeyFromValue, schoolDayStartIso, schoolWeekBounds } from "@/shared/lib/schoolTime";
import { ActionMenu, type ActionMenuItem } from "@/shared/ui/ActionMenu";
import { Drawer } from "@/shared/ui/Drawer";
import type { FloatingToastTone } from "@/shared/ui/FloatingToast";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";
import { StatusBadge } from "@/shared/ui/StatusBadge";

type ScheduleMode = "agenda" | "week";
type AppointmentData = { items: RecruitmentAppointment[]; total: number; page: number; total_pages: number };
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
  const endsAt = new Date(item.ends_at);
  if (Number.isNaN(startsAt.getTime())) return "Time not set";
  const start = scheduleTimeFormatter.format(startsAt);
  return Number.isNaN(endsAt.getTime()) ? start : `${start}–${scheduleTimeFormatter.format(endsAt)}`;
}

function appointmentTitle(item: RecruitmentAppointment) {
  return item.appointment_type === "job_interview" ? "Job interview" : "Demo lesson";
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
  onStatus: (item: RecruitmentAppointment, status: "cancelled" | "no_show") => void;
}) {
  const actions: ActionMenuItem[] = item.status === "scheduled" && canManage
    ? [
        { key: "edit", label: "Reschedule", icon: <Pencil className="h-4 w-4" />, onClick: () => onEdit(item) },
        { key: "no_show", label: "Mark no-show", icon: <UserX className="h-4 w-4" />, onClick: () => onStatus(item, "no_show") },
        { separator: true, key: "separator" },
        { key: "cancel", label: "Cancel appointment", icon: <Ban className="h-4 w-4" />, danger: true, onClick: () => onStatus(item, "cancelled") },
      ]
    : [];
  const candidateName = item.candidate_name || "Candidate";
  const effectiveStatus = item.is_overdue && item.status === "scheduled" ? "overdue" : item.status;
  const overdueClass = effectiveStatus === "overdue" ? "border-red-400 bg-red-50 dark:border-red-500/50 dark:bg-red-950/20" : "border-border bg-card";

  if (compact) {
    return (
      <article className={`min-w-0 rounded-lg border p-2 shadow-sm ${overdueClass}`}>
        <div className="flex min-w-0 items-start gap-1">
          <a
            href={`${basePath}/candidates/${item.candidate_id}?tab=evaluations&origin=schedule`}
            onClick={() => rememberRecruitmentReturn("schedule")}
            className="min-w-0 flex-1 rounded-md py-1 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
            title={candidateName}
          >
            <p className="truncate text-[13px] font-semibold hover:text-primary">{candidateName}</p>
          </a>
          {actions.length ? <ActionMenu items={actions} label={`Actions for ${candidateName}`} /> : null}
        </div>
        <p className="mt-1 text-xs font-medium text-muted-foreground">{appointmentTitle(item)}</p>
        <p className="mt-1 text-[13px] font-semibold tabular-nums text-foreground">{appointmentTimeLabel(item)}</p>
        <div className="mt-2 flex min-w-0 items-center justify-between gap-1.5">
          <span className="min-w-0 truncate text-[11px] text-muted-foreground" title={item.responsible_name || "Staff not assigned"}>
            {item.responsible_name || "Staff not assigned"}
          </span>
          <StatusBadge status={effectiveStatus} className="shrink-0 text-[9px]" />
        </div>
        {item.appointment_format ? <p className="mt-1 truncate text-[11px] text-muted-foreground">{item.appointment_format}</p> : null}
        {item.topic ? <p className="mt-1 truncate text-[11px] text-muted-foreground">Topic: {item.topic}</p> : null}
      </article>
    );
  }

  return (
    <article className={`rounded-lg border p-3 shadow-sm ${overdueClass}`}>
      <div className="flex items-start justify-between gap-2">
        <a href={`${basePath}/candidates/${item.candidate_id}?tab=evaluations&origin=schedule`} onClick={() => rememberRecruitmentReturn("schedule")} className="min-w-0 rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30">
          <p className="truncate text-sm font-semibold hover:text-primary">{candidateName}</p>
          <p className="mt-0.5 text-xs font-medium text-muted-foreground">{appointmentTitle(item)} · {dateLabel(item.starts_at)}</p>
        </a>
        <div className="flex shrink-0 items-center gap-1"><StatusBadge status={effectiveStatus} />{actions.length ? <ActionMenu items={actions} label={`Actions for ${candidateName}`} /> : null}</div>
      </div>
      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
        <span>{item.responsible_name || "Staff not assigned"}</span>
        {item.appointment_format ? <span>{item.appointment_format}</span> : null}
        {item.location_or_link ? <span className="max-w-full truncate">{item.location_or_link}</span> : null}
        {item.topic ? <span className="max-w-full truncate">Topic: {item.topic}</span> : null}
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
  const [mode, setMode] = useState<ScheduleMode>(initial.get("mode") === "week" ? "week" : "agenda");
  const [anchor, setAnchor] = useState(() => schoolDateKeyFromValue(initial.get("date")) || schoolDateKey());
  const [type, setType] = useState(initial.get("appointment_type") || "");
  const [status, setStatus] = useState(initial.get("status") || "scheduled");
  const [staffId, setStaffId] = useState(initial.get("responsible_account_id") || "");
  const [editing, setEditing] = useState<RecruitmentAppointment | null>(null);
  const [statusAction, setStatusAction] = useState<{ item: RecruitmentAppointment; status: "cancelled" | "no_show" } | null>(null);
  const [conflicts, setConflicts] = useState<RecruitmentAppointment[]>([]);
  const bounds = mode === "week"
    ? schoolWeekBounds(new Date(`${anchor}T12:00:00Z`))
    : { start: anchor, end: addDaysToDateKey(anchor, 29) };
  const rangeEnd = addDaysToDateKey(bounds.end, 1);
  const query = new URLSearchParams({
    page: "1",
    per_page: "100",
    from: schoolDayStartIso(bounds.start),
    to: schoolDayStartIso(rangeEnd),
  });
  if (type) query.set("appointment_type", type);
  if (status) query.set("status", status);
  if (staffId) query.set("responsible_account_id", staffId);
  const appointments = useQuery({
    queryKey: ["recruitment", "appointments", bounds.start, bounds.end, type, status, staffId],
    queryFn: () => recruitmentRequest<AppointmentData>(`${RECRUITMENT_API}/appointments?${query}`),
  });
  const mutation = useMutation({
    mutationFn: ({ url, method = "POST", values }: { url: string; method?: string; values: unknown }) => recruitmentRequest<MutationPayload>(url, { method, body: jsonBody(values) }),
    onSuccess: (result) => {
      onAnnouncement(result.message || "Appointment updated.");
      setEditing(null);
      setStatusAction(null);
      setConflicts([]);
      void queryClient.invalidateQueries({ queryKey: ["recruitment"] });
    },
    onError: (error) => {
      const overlap = appointmentConflictDetails<RecruitmentAppointment>(error);
      if (overlap.length) setConflicts(overlap);
      onAnnouncement(queryError(error), "error");
    },
  });
  useEffect(() => {
    replaceUrlParams({
      mode: mode === "agenda" ? "" : mode,
      date: anchor === schoolDateKey() ? "" : anchor,
      appointment_type: type,
      status: status === "scheduled" ? "" : status,
      responsible_account_id: staffId,
    });
  }, [anchor, mode, staffId, status, type]);
  useEffect(() => {
    if (appointments.data) restoreRecruitmentReturn("schedule");
  }, [appointments.data]);
  const weekDays = useMemo(() => Array.from({ length: 7 }, (_, index) => addDaysToDateKey(bounds.start, index)), [bounds.start]);
  const itemsForDay = (date: string) => (appointments.data?.items || []).filter((item) => schoolDateKeyFromValue(item.starts_at) === date);
  const canManage = role === "hr_manager" || role === "ceo";
  const moveRange = (direction: -1 | 1) => setAnchor(addDaysToDateKey(anchor, direction * (mode === "week" ? 7 : 30)));
  const submitEdit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editing) return;
    mutation.mutate({
      url: `${RECRUITMENT_API}/candidates/${editing.candidate_id}/appointments/${editing.id}`,
      method: "PATCH",
      values: { ...formValues(event.currentTarget), expected_version: editing.version, allow_conflict: Boolean(conflicts.length) },
    });
  };

  if (appointments.isLoading) return <PageState>Loading recruitment schedule…</PageState>;
  if (appointments.error || !appointments.data) return <PageState tone="error">{queryError(appointments.error)}</PageState>;

  const agenda = (
    <div className="space-y-3">
      {appointments.data.items.map((item) => <AppointmentCard key={item.id} item={item} basePath={basePath} canManage={canManage} onEdit={(value) => { setConflicts([]); setEditing(value); }} onStatus={(value, nextStatus) => setStatusAction({ item: value, status: nextStatus })} />)}
      {!appointments.data.items.length ? <EmptyLine>No appointments in this period.</EmptyLine> : null}
    </div>
  );

  return (
    <div className="space-y-3">
      <section className="rounded-xl border border-border bg-card p-3">
        <div className="flex flex-wrap items-end gap-2">
          <div className="inline-flex min-h-11 rounded-lg border border-border bg-muted/40 p-1">
            <button type="button" onClick={() => setMode("agenda")} aria-pressed={mode === "agenda"} className={`inline-flex min-h-9 items-center gap-1.5 rounded-md px-3 text-xs font-semibold ${mode === "agenda" ? "bg-primary text-primary-foreground" : "text-muted-foreground"}`}><List className="h-4 w-4" />Agenda</button>
            <button type="button" onClick={() => setMode("week")} aria-pressed={mode === "week"} className={`hidden min-h-9 items-center gap-1.5 rounded-md px-3 text-xs font-semibold md:inline-flex ${mode === "week" ? "bg-primary text-primary-foreground" : "text-muted-foreground"}`}><CalendarDays className="h-4 w-4" />Week</button>
          </div>
          <div className="inline-flex min-h-11 items-center rounded-lg border border-border">
            <button type="button" className="flex h-11 w-11 items-center justify-center" onClick={() => moveRange(-1)} aria-label="Previous schedule period"><ChevronLeft className="h-4 w-4" /></button>
            <button type="button" className="min-h-11 border-x border-border px-3 text-xs font-semibold" onClick={() => setAnchor(schoolDateKey())}>Today</button>
            <button type="button" className="flex h-11 w-11 items-center justify-center" onClick={() => moveRange(1)} aria-label="Next schedule period"><ChevronRight className="h-4 w-4" /></button>
          </div>
          <label className="min-w-36 flex-1 text-xs font-semibold text-muted-foreground">Type<select className={`${fieldClass} mt-1`} value={type} onChange={(event) => setType(event.target.value)}><option value="">All types</option><option value="job_interview">Job interviews</option><option value="demo_lesson">Demo lessons</option></select></label>
          <label className="min-w-36 flex-1 text-xs font-semibold text-muted-foreground">Status<select className={`${fieldClass} mt-1`} value={status} onChange={(event) => setStatus(event.target.value)}><option value="scheduled">Scheduled</option><option value="in_progress">In progress</option><option value="completed">Completed</option><option value="cancelled">Cancelled</option><option value="no_show">No-show</option><option value="">All statuses</option></select></label>
          <label className="min-w-44 flex-1 text-xs font-semibold text-muted-foreground">Staff<select className={`${fieldClass} mt-1`} value={staffId} onChange={(event) => setStaffId(event.target.value)}><option value="">All staff</option>{options?.staff.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}</select></label>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">{scheduleDateLabel(bounds.start)} – {scheduleDateLabel(bounds.end)} · Asia/Tashkent</p>
      </section>

      <div className="md:hidden">{agenda}</div>
      <div className="hidden md:block">
        {mode === "agenda" ? agenda : (
          <div className="overflow-x-auto rounded-xl border border-border bg-card">
            <section className="grid min-w-[70rem] grid-cols-7">
              {weekDays.map((day) => (
                <div key={day} className="min-w-0 border-r border-border last:border-r-0">
                  <div className="sticky top-0 z-10 border-b border-border bg-muted px-2 py-2 text-center text-[11px] font-semibold uppercase tracking-wide">{scheduleDayLabel(day)}</div>
                  <div className="min-h-56 space-y-2 p-2">
                    {itemsForDay(day).map((item) => <AppointmentCard key={item.id} item={item} basePath={basePath} canManage={canManage} compact onEdit={(value) => { setConflicts([]); setEditing(value); }} onStatus={(value, nextStatus) => setStatusAction({ item: value, status: nextStatus })} />)}
                    {!itemsForDay(day).length ? <p className="py-4 text-center text-[11px] text-muted-foreground">No appointments</p> : null}
                  </div>
                </div>
              ))}
            </section>
          </div>
        )}
      </div>

      <Drawer open={Boolean(editing)} onClose={() => { if (!mutation.isPending) { setEditing(null); setConflicts([]); } }} title="Reschedule appointment" description={editing?.candidate_name} footer={<div className="flex justify-end gap-2"><button type="button" className={secondaryButtonClass} onClick={() => setEditing(null)} disabled={mutation.isPending}>Cancel</button><button type="submit" form="schedule-edit-form" className={buttonClass} disabled={mutation.isPending}>{conflicts.length ? "Schedule anyway" : "Save appointment"}</button></div>}>
        {editing ? <form id="schedule-edit-form" onSubmit={submitEdit}><AppointmentForm appointmentType={editing.appointment_type} appointment={editing} options={options} conflicts={conflicts} /></form> : null}
      </Drawer>

      <Modal open={Boolean(statusAction)} onClose={() => { if (!mutation.isPending) setStatusAction(null); }} title={statusAction?.status === "cancelled" ? "Cancel appointment" : "Mark no-show"} subtitle={statusAction?.item.candidate_name} size="sm">
        {statusAction ? <form onSubmit={(event) => { event.preventDefault(); const values = formValues(event.currentTarget); mutation.mutate({ url: `${RECRUITMENT_API}/candidates/${statusAction.item.candidate_id}/appointments/${statusAction.item.id}/${statusAction.status === "cancelled" ? "cancel" : "no-show"}`, values: { expected_version: statusAction.item.version, reason: values.reason } }); }}><ModalBody><label className="text-xs font-semibold">Reason / note<textarea autoFocus required={statusAction.status === "cancelled"} name="reason" className={`${fieldClass} mt-1 min-h-24`} /></label></ModalBody><ModalFooter><div className="flex justify-end gap-2"><button type="button" className={secondaryButtonClass} onClick={() => setStatusAction(null)}>Back</button><button type="submit" className={buttonClass}>{statusAction.status === "cancelled" ? "Cancel appointment" : "Mark no-show"}</button></div></ModalFooter></form> : null}
      </Modal>
    </div>
  );
}
