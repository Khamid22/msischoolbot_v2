import { AlertTriangle } from "lucide-react";

import { humanize, type RecruitmentAppointment, type RecruitmentOptions } from "@/features/recruitment/model";
import { fieldClass } from "@/features/recruitment/ui";

function tashkentInputValue(value?: string) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Tashkent",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date);
  const part = (type: Intl.DateTimeFormatPartTypes) => parts.find((item) => item.type === type)?.value || "";
  return `${part("year")}-${part("month")}-${part("day")}T${part("hour")}:${part("minute")}`;
}

function appointmentDuration(appointment?: RecruitmentAppointment) {
  if (!appointment) return 0;
  const starts = new Date(appointment.starts_at).getTime();
  const ends = new Date(appointment.ends_at).getTime();
  return Number.isFinite(starts) && Number.isFinite(ends) ? Math.round((ends - starts) / 60_000) : 0;
}

export function AppointmentForm({
  appointmentType,
  options,
  appointment,
  conflicts = [],
}: {
  appointmentType: "job_interview" | "demo_lesson";
  options?: RecruitmentOptions;
  appointment?: RecruitmentAppointment;
  conflicts?: RecruitmentAppointment[];
}) {
  const demo = appointmentType === "demo_lesson";
  const staff = (options?.staff || []).filter((person) => (
    demo
      ? ["academic_director", "head_of_department"].includes(person.role)
      : ["hr_manager", "ceo"].includes(person.role)
  ));
  const defaultDuration = appointmentDuration(appointment) || (demo ? 45 : 30);
  return (
    <div className="grid gap-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-xs font-semibold">
          Date and start time
          <input
            autoFocus
            required
            name="starts_at"
            type="datetime-local"
            defaultValue={tashkentInputValue(appointment?.starts_at)}
            className={`${fieldClass} mt-1`}
          />
        </label>
        <label className="text-xs font-semibold">
          Duration (minutes)
          <input
            required
            name="duration_minutes"
            type="number"
            min={15}
            max={240}
            step={1}
            defaultValue={defaultDuration}
            className={`${fieldClass} mt-1`}
          />
        </label>
      </div>
      <label className="text-xs font-semibold">
        {demo ? "Demo evaluator" : "Responsible interviewer"}
        <select
          name="responsible_account_id"
          required={demo}
          defaultValue={appointment?.responsible_account_id || ""}
          className={`${fieldClass} mt-1`}
        >
          <option value="">{demo ? "Select evaluator" : "Not assigned"}</option>
          {staff.map((person) => <option key={person.id} value={person.id}>{person.name} · {humanize(person.role)}</option>)}
        </select>
      </label>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-xs font-semibold">Format<input name="appointment_format" defaultValue={appointment?.appointment_format} placeholder={demo ? "In person or online" : "In person, online or phone"} className={`${fieldClass} mt-1`} /></label>
        <label className="text-xs font-semibold">Location or link<input name="location_or_link" defaultValue={appointment?.location_or_link} className={`${fieldClass} mt-1`} /></label>
      </div>
      {demo ? <label className="text-xs font-semibold">Demo topic<input name="topic" defaultValue={appointment?.topic} className={`${fieldClass} mt-1`} /></label> : null}
      <label className="text-xs font-semibold">Notes<textarea name="note" defaultValue={appointment?.note} className={`${fieldClass} mt-1 min-h-24`} /></label>
      {conflicts.length ? (
        <div role="alert" className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-900 dark:text-amber-200">
          <p className="flex items-center gap-2 font-semibold"><AlertTriangle className="h-4 w-4" />Schedule conflict</p>
          <p className="mt-1 text-xs leading-5">The responsible staff member already has {conflicts.length} overlapping recruitment appointment{conflicts.length === 1 ? "" : "s"}. Submit again to schedule anyway.</p>
        </div>
      ) : null}
    </div>
  );
}
