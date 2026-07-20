import { useState } from "react";

import {
  humanize,
  type RecruitmentAppointment,
  type RecruitmentOptions,
} from "@/features/recruitment/model";
import { fieldClass } from "@/features/recruitment/ui";

function tashkentInputValue(value?: string) {
  const date = value
    ? new Date(value)
    : new Date(
        Math.ceil((Date.now() + 60 * 60_000) / (15 * 60_000)) *
          (15 * 60_000),
      );
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
  const part = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((item) => item.type === type)?.value || "";
  return `${part("year")}-${part("month")}-${part("day")}T${part("hour")}:${part("minute")}`;
}

export function AppointmentForm({
  appointmentType,
  options,
  appointment,
}: {
  appointmentType: "job_interview" | "demo_lesson";
  options?: RecruitmentOptions;
  appointment?: RecruitmentAppointment;
}) {
  const demo = appointmentType === "demo_lesson";
  const [format, setFormat] = useState(
    appointment?.appointment_format || "",
  );
  const initialStart = tashkentInputValue(appointment?.starts_at);
  const [appointmentDate, setAppointmentDate] = useState(
    initialStart.slice(0, 10),
  );
  const [appointmentTime, setAppointmentTime] = useState(
    initialStart.slice(11, 16),
  );
  const staff = (options?.staff || []).filter((person) =>
    ["academic_director", "head_of_department"].includes(person.role),
  );

  return (
    <div className="grid gap-2">
      <input
        type="hidden"
        name="starts_at"
        value={
          appointmentDate && appointmentTime
            ? `${appointmentDate}T${appointmentTime}`
            : ""
        }
      />
      <div className="grid gap-2 sm:grid-cols-2">
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
            step={60}
            value={appointmentTime}
            onChange={(event) => setAppointmentTime(event.target.value)}
            className={`${fieldClass} mt-1`}
          />
        </label>
      </div>

      {demo ? (
        <label className="text-xs font-semibold">
          Demo evaluator
          <select
            name="responsible_account_id"
            required
            defaultValue={appointment?.responsible_account_id || ""}
            className={`${fieldClass} mt-1`}
          >
            <option value="">Select evaluator</option>
            {staff.map((person) => (
              <option key={person.id} value={person.id}>
                {person.name} · {humanize(person.role)}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      <div className="grid gap-2 sm:grid-cols-2">
        <label className="text-xs font-semibold">
          Format
          <select
            required
            name="appointment_format"
            value={format}
            onChange={(event) => setFormat(event.target.value)}
            className={`${fieldClass} mt-1`}
          >
            <option value="">Select format</option>
            <option value="Online">Online</option>
            <option value="In person">In person</option>
            {!demo ? <option value="Phone">Phone</option> : null}
          </select>
        </label>
        <label className="text-xs font-semibold">
          {format === "Online"
            ? "Conference link (optional)"
            : format === "In person"
              ? "Location (optional)"
              : "Location or link (optional)"}
          <input
            type={format === "Online" ? "url" : "text"}
            name="location_or_link"
            defaultValue={appointment?.location_or_link}
            placeholder={format === "Online" ? "https://meet.example/..." : ""}
            className={`${fieldClass} mt-1`}
          />
        </label>
      </div>

      {demo ? (
        <label className="text-xs font-semibold">
          Demo topic
          <input
            name="topic"
            defaultValue={appointment?.topic}
            className={`${fieldClass} mt-1`}
          />
        </label>
      ) : null}
    </div>
  );
}
