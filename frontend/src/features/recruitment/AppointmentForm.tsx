import { AlertTriangle } from "lucide-react";
import { useState } from "react";

import { humanize, type RecruitmentAppointment, type RecruitmentOptions } from "@/features/recruitment/model";
import { fieldClass } from "@/features/recruitment/ui";

function tashkentInputValue(value?: string) {
  const date = value ? new Date(value) : new Date(Math.ceil((Date.now() + 60 * 60_000) / (15 * 60_000)) * (15 * 60_000));
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
  const [format, setFormat] = useState(appointment?.appointment_format || "");
  const initialStart = tashkentInputValue(appointment?.starts_at);
  const [appointmentDate, setAppointmentDate] = useState(initialStart.slice(0, 10));
  const [appointmentTime, setAppointmentTime] = useState(initialStart.slice(11, 16));
  const staff = (options?.staff || []).filter((person) => (
    demo
      ? ["academic_director", "head_of_department"].includes(person.role)
      : ["hr_manager", "ceo"].includes(person.role)
  ));
  const defaultDuration = appointmentDuration(appointment) || (demo ? 45 : 30);
  return (
    <div className="grid gap-3">
      <div className="flex items-center justify-between gap-3 rounded-lg bg-muted/60 px-3 py-2 text-xs text-muted-foreground">
        <span>Appointment time</span><strong className="text-foreground">Asia/Tashkent (UTC+5)</strong>
      </div>
      <input type="hidden" name="starts_at" value={appointmentDate && appointmentTime ? `${appointmentDate}T${appointmentTime}` : ""} />
      <div className="grid gap-3 sm:grid-cols-3">
        <label className="text-xs font-semibold">
          Date
          <input
            autoFocus
            required
            type="date"
            value={appointmentDate}
            onChange={(event) => setAppointmentDate(event.target.value)}
            className={`${fieldClass} mt-1`}
          />
        </label>
        <label className="text-xs font-semibold">
          Time
          <input
            required
            type="time"
            step={900}
            value={appointmentTime}
            onChange={(event) => setAppointmentTime(event.target.value)}
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
            step={15}
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
        <label className="text-xs font-semibold">Format<select required name="appointment_format" value={format} onChange={(event) => setFormat(event.target.value)} className={`${fieldClass} mt-1`}><option value="">Select format</option><option value="Online">Online</option><option value="In person">In person</option>{!demo ? <option value="Phone">Phone</option> : null}</select></label>
        <label className="text-xs font-semibold">{format === "Online" ? "Conference link (optional)" : format === "In person" ? "Location (optional)" : "Location or link (optional)"}<input type={format === "Online" ? "url" : "text"} name="location_or_link" defaultValue={appointment?.location_or_link} placeholder={format === "Online" ? "https://meet.example/..." : ""} className={`${fieldClass} mt-1`} /></label>
      </div>
      {demo ? <label className="text-xs font-semibold">Demo topic<input name="topic" defaultValue={appointment?.topic} className={`${fieldClass} mt-1`} /></label> : null}
      {conflicts.length ? (
        <div role="alert" className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-900 dark:text-amber-200">
          <p className="flex items-center gap-2 font-semibold"><AlertTriangle className="h-4 w-4" />Schedule conflict</p>
          <p className="mt-1 text-xs leading-5">The responsible staff member already has {conflicts.length} overlapping recruitment appointment{conflicts.length === 1 ? "" : "s"}. Submit again to schedule anyway.</p>
        </div>
      ) : null}
    </div>
  );
}
