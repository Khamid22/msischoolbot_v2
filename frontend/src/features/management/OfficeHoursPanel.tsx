import { useState, useEffect } from "react";
import { CalendarDays, Clock, Plus, Trash, Check, X, Users, AlertCircle } from "lucide-react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { JSON_HEADERS, XHR_HEADERS } from "@/shared/lib/api";
import {
  SCHOOL_TIME_ZONE,
  schoolDateKey,
  schoolDateKeyFromValue,
  schoolLocalDateTimeToIso,
  schoolWeekBounds,
} from "@/shared/lib/schoolTime";
import { useDismissibleLayer } from "@/shared/lib/useDismissibleLayer";

type Availability = {
  id: number;
  teacher_id: number;
  teacher_name: string;
  subject_id: number | null;
  subject_name: string | null;
  planned_topic: string;
  starts_at: string;
  ends_at: string;
  slot_minutes: number;
  room: string;
  capacity: number;
  status: string;
  booked_count: number;
};

type Booking = {
  id: number;
  availability_id: number;
  teacher_id: number;
  teacher_name: string;
  student_row_id: number;
  student_name: string;
  subject_id: number | null;
  subject_name: string | null;
  starts_at: string;
  ends_at: string;
  status: string;
  student_topic_request: string;
  student_note: string;
  teacher_note: string;
  created_at: string;
};

type TeacherOption = {
  id: number;
  full_name: string;
  assigned_group?: string;
};

type SubjectOption = {
  id: number;
  name: string;
};

function cleanText(value: unknown) {
  return String(value || "").trim();
}

function normalizeText(value: unknown) {
  return cleanText(value).toLowerCase();
}

export default function OfficeHoursPanel({ state }: { state: any }) {
  const [availabilities, setAvailabilities] = useState<Availability[]>([]);
  const [selectedSlot, setSelectedSlot] = useState<Availability | null>(null);
  const [slotBookings, setSlotBookings] = useState<Booking[]>([]);
  const [teachers, setTeachers] = useState<TeacherOption[]>([]);
  const [subjects, setSubjects] = useState<SubjectOption[]>([]);

  // Filter states
  const [dateFilter, setDateFilter] = useState<"all" | "today" | "week">("all");
  const [teacherFilter, setTeacherFilter] = useState<string>("all");
  const [subjectFilter, setSubjectFilter] = useState<string>("all");

  // Create availability modal state
  const [createOpen, setCreateOpen] = useState(false);
  useDismissibleLayer({
    enabled: createOpen,
    onDismiss: () => setCreateOpen(false),
    dismissOnOutsidePointer: false,
  });
  const [newTeacherId, setNewTeacherId] = useState("");
  const [newSubjectId, setNewSubjectId] = useState("");
  const [newPlannedTopic, setNewPlannedTopic] = useState("");
  const [newSessionDate, setNewSessionDate] = useState("");
  const [newStartTime, setNewStartTime] = useState("");
  const [newSlotMinutes, setNewSlotMinutes] = useState("30");
  const [newRoom, setNewRoom] = useState("");
  const [newCapacity, setNewCapacity] = useState("1");
  const [errorMsg, setErrorMsg] = useState("");

  const csrfToken = state.props?.csrfToken || "";
  const academicGroups = Array.isArray(state.props?.adminAcademicGroups)
    ? (state.props.adminAcademicGroups as Array<Record<string, unknown>>)
    : [];

  useEffect(() => {
    fetchData();
    // Load filter options
    if (Array.isArray(state.teachers)) {
      setTeachers(state.teachers.map((t: any) => ({ id: t.id, full_name: t.full_name, assigned_group: t.assigned_group })));
    } else if (Array.isArray(state.props?.adminTeachers)) {
      setTeachers(state.props.adminTeachers.map((t: any) => ({ id: t.id, full_name: t.full_name, assigned_group: t.assigned_group })));
    }

    if (Array.isArray(state.props?.adminAcademicSubjects)) {
      setSubjects(state.props.adminAcademicSubjects.map((s: any) => ({ id: s.id, name: s.name })));
    }
  }, [state.teachers, state.props?.adminTeachers, state.props?.adminAcademicSubjects]);

  const subjectNameById = new Map(subjects.map((subject) => [Number(subject.id), cleanText(subject.name)]));

  const teacherOptionsForSubject = (subjectId: string) => {
    if (!subjectId) return [];
    const selectedSubjectId = Number(subjectId);
    const selectedSubjectName = subjectNameById.get(selectedSubjectId) || "";
    const groupNamesForSubject = new Set(
      academicGroups
        .filter((group) => {
          const groupSubjectId = Number(group.subject_id || 0);
          const groupSubjectName = cleanText(group.subject_name);
          return (
            (groupSubjectId > 0 && groupSubjectId === selectedSubjectId) ||
            (!!selectedSubjectName && normalizeText(groupSubjectName) === normalizeText(selectedSubjectName))
          );
        })
        .map((group) => normalizeText(group.name || group.group_name))
        .filter(Boolean),
    );

    if (groupNamesForSubject.size === 0) {
      return [];
    }

    return teachers.filter((teacher) => groupNamesForSubject.has(normalizeText(teacher.assigned_group)));
  };

  const filteredTeachers = subjectFilter === "all" ? teachers : teacherOptionsForSubject(subjectFilter);
  const teachersForNewSubject = teacherOptionsForSubject(newSubjectId);

  const fetchData = async () => {
    try {
      const res = await fetch("/api/v1/admin/office-hours/availability", {
        headers: XHR_HEADERS
      });
      if (res.ok) {
        const data = await res.json();
        setAvailabilities(data.data?.availabilities || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (selectedSlot) {
      fetchBookingsForSlot(selectedSlot.id);
    } else {
      setSlotBookings([]);
    }
  }, [selectedSlot]);

  const fetchBookingsForSlot = async (slotId: number) => {
    try {
      const res = await fetch(`/api/v1/admin/office-hours/bookings?availability_id=${slotId}`, {
        headers: XHR_HEADERS
      });
      if (res.ok) {
        const data = await res.json();
        setSlotBookings(data.data?.bookings || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleCreateAvailability = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");

    if (!newSubjectId || !newTeacherId || !newSessionDate || !newStartTime) {
      setErrorMsg("Please select a subject, teacher, date, and start time.");
      return;
    }

    const slotMinutes = Math.max(1, Number(newSlotMinutes) || 30);
    const startsAt = schoolLocalDateTimeToIso(newSessionDate, newStartTime);
    if (!startsAt) {
      setErrorMsg("Please enter a valid date and start time.");
      return;
    }
    const startsAtDate = new Date(startsAt);
    const endsAtDate = new Date(startsAtDate.getTime() + slotMinutes * 60_000);

    try {
      const res = await fetch("/api/v1/admin/office-hours/availability", {
        method: "POST",
        headers: JSON_HEADERS,
        body: JSON.stringify({
          teacher_id: Number(newTeacherId),
          subject_id: Number(newSubjectId),
          planned_topic: newPlannedTopic,
          starts_at: startsAt,
          ends_at: endsAtDate.toISOString(),
          slot_minutes: slotMinutes,
          room: newRoom,
          capacity: Number(newCapacity),
          csrf_token: csrfToken
        })
      });

      const data = await res.json();
      if (res.ok && data.status === "success") {
        setCreateOpen(false);
        // Reset form
        setNewTeacherId("");
        setNewSubjectId("");
        setNewPlannedTopic("");
        setNewSessionDate("");
        setNewStartTime("");
        setNewRoom("");
        setNewCapacity("1");
        fetchData();
      } else {
        setErrorMsg(data.message || "Failed to create availability.");
      }
    } catch (err) {
      setErrorMsg("Network error. Please try again.");
    }
  };

  const handleCancelSlot = async (id: number) => {
    if (!confirm("Are you sure you want to cancel this availability slot? All active bookings for it will also be cancelled.")) return;
    try {
      const res = await fetch(`/api/v1/admin/office-hours/availability/${id}`, {
        method: "PATCH",
        headers: JSON_HEADERS,
        body: JSON.stringify({
          status: "cancelled",
          csrf_token: csrfToken
        })
      });
      if (res.ok) {
        fetchData();
        if (selectedSlot?.id === id) {
          setSelectedSlot(prev => prev ? { ...prev, status: "cancelled" } : null);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleUpdateBookingStatus = async (bookingId: number, status: string) => {
    try {
      const res = await fetch(`/api/v1/admin/office-hours/bookings/${bookingId}`, {
        method: "PATCH",
        headers: JSON_HEADERS,
        body: JSON.stringify({
          status,
          csrf_token: csrfToken
        })
      });
      if (res.ok && selectedSlot) {
        fetchBookingsForSlot(selectedSlot.id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Filtering logic
  const todayKey = schoolDateKey();
  const currentWeek = schoolWeekBounds();
  const filteredSlots = availabilities.filter((slot) => {
    // 1. Date filter
    const startsKey = schoolDateKeyFromValue(slot.starts_at);
    if (dateFilter === "today") {
      if (startsKey !== todayKey) return false;
    } else if (dateFilter === "week") {
      if (startsKey < currentWeek.start || startsKey > currentWeek.end) return false;
    }

    // 2. Teacher filter
    if (teacherFilter !== "all" && String(slot.teacher_id) !== teacherFilter) {
      return false;
    }

    // 3. Subject filter
    if (subjectFilter !== "all" && String(slot.subject_id) !== subjectFilter) {
      return false;
    }

    return true;
  });

  const formatDate = (isoStr: string) => {
    const d = new Date(isoStr);
    return d.toLocaleDateString(undefined, { timeZone: SCHOOL_TIME_ZONE, weekday: 'short', month: 'short', day: 'numeric' });
  };

  const formatTime = (isoStr: string) => {
    const d = new Date(isoStr);
    return d.toLocaleTimeString(undefined, { timeZone: SCHOOL_TIME_ZONE, hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="space-y-4">
      {/* Top Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-foreground/10 bg-surface px-4 py-3 shadow-card">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex rounded-lg border border-foreground/10 p-0.5 bg-background">
            {(["all", "today", "week"] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setDateFilter(mode)}
                className={`rounded-md px-3 py-1.5 text-xs font-bold capitalize transition-colors ${
                  dateFilter === mode ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {mode === "all" ? "All Time" : mode}
              </button>
            ))}
          </div>

          <select
            value={subjectFilter}
            onChange={(e) => {
              setSubjectFilter(e.target.value);
              setTeacherFilter("all");
            }}
            className="rounded-lg border border-foreground/10 bg-background px-3 py-1.5 text-xs font-semibold outline-none focus:border-foreground/30"
            aria-label="Subject Filter"
          >
            <option value="all">All Subjects</option>
            {subjects.map((s) => (
              <option key={s.id} value={String(s.id)}>{s.name}</option>
            ))}
          </select>

          <select
            value={teacherFilter}
            onChange={(e) => setTeacherFilter(e.target.value)}
            className="rounded-lg border border-foreground/10 bg-background px-3 py-1.5 text-xs font-semibold outline-none focus:border-foreground/30"
            aria-label="Teacher Filter"
          >
            <option value="all">All Teachers</option>
            {filteredTeachers.map((t) => (
              <option key={t.id} value={String(t.id)}>{t.full_name}</option>
            ))}
          </select>
        </div>

        <button
          type="button"
          onClick={() => setCreateOpen(true)}
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-bold text-primary-foreground hover:bg-primary/95"
        >
          <Plus className="h-3.5 w-3.5" />
          Create Availability
        </button>
      </div>

      {/* Main split layout */}
      <div className="grid gap-4 lg:grid-cols-[1.8fr_1fr] items-start">
        {/* Left Side: 65% width */}
        <ChartCard
          title="Availability Slots"
          subtitle={`${filteredSlots.length} available sessions`}
          icon={<CalendarDays className="h-4 w-4 text-info" />}
        >
          <div className="miniapp-table-scroll rounded-lg border border-foreground/10">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-surface shadow-[0_1px_0_hsl(var(--foreground)/0.08)]">
                <tr className="border-b border-foreground/5">
                  <th className="px-3 py-2 font-bold uppercase text-muted-foreground">Date</th>
                  <th className="px-3 py-2 font-bold uppercase text-muted-foreground">Time</th>
                  <th className="px-3 py-2 font-bold uppercase text-muted-foreground">Teacher</th>
                  <th className="px-3 py-2 font-bold uppercase text-muted-foreground">Subject</th>
                  <th className="px-3 py-2 font-bold uppercase text-muted-foreground">Topic</th>
                  <th className="px-3 py-2 font-bold uppercase text-muted-foreground">Room</th>
                  <th className="px-3 py-2 text-center font-bold uppercase text-muted-foreground">Booked</th>
                  <th className="px-3 py-2 font-bold uppercase text-muted-foreground">Status</th>
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-foreground/5 bg-background">
                {filteredSlots.map((slot) => {
                  const isSelected = selectedSlot?.id === slot.id;
                  const isCancelled = slot.status === "cancelled";
                  return (
                    <tr
                      key={slot.id}
                      onClick={() => setSelectedSlot(slot)}
                      className={`cursor-pointer transition-colors hover:bg-primary/5 ${
                        isSelected ? "bg-primary/10 text-primary font-medium" : ""
                      }`}
                    >
                      <td className="px-3 py-3 whitespace-nowrap">{formatDate(slot.starts_at)}</td>
                      <td className="px-3 py-3 whitespace-nowrap">
                        {formatTime(slot.starts_at)} - {formatTime(slot.ends_at)}
                      </td>
                      <td className="px-3 py-3 font-semibold whitespace-nowrap">{slot.teacher_name}</td>
                      <td className="px-3 py-3 whitespace-nowrap">{slot.subject_name || "—"}</td>
                      <td className="max-w-[14rem] truncate px-3 py-3" title={slot.planned_topic || ""}>
                        {slot.planned_topic || "Open questions"}
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap">{slot.room || "—"}</td>
                      <td className="px-3 py-3 text-center whitespace-nowrap font-bold">
                        {slot.booked_count} / {slot.capacity}
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap">
                        <span className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-bold uppercase ${
                          isCancelled ? "bg-muted text-muted-foreground border border-foreground/10" : "bg-emerald-50 text-emerald-700 border border-emerald-200"
                        }`}>
                          {slot.status}
                        </span>
                      </td>
                      <td className="px-3 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                        {!isCancelled && (
                          <button
                            type="button"
                            onClick={() => handleCancelSlot(slot.id)}
                            className="rounded-lg p-1 text-destructive hover:bg-destructive/10"
                            title="Cancel slot"
                          >
                            <Trash className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
                {filteredSlots.length === 0 && (
                  <tr>
                    <td colSpan={9} className="p-8 text-center text-sm text-muted-foreground">
                      No availability slots found matching filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </ChartCard>

        {/* Right Side: 35% width */}
        <ChartCard
          title="Booking Details"
          subtitle={selectedSlot ? `${selectedSlot.teacher_name} - ${formatDate(selectedSlot.starts_at)}` : "Select a slot"}
          icon={<Users className="h-4 w-4 text-info" />}
        >
          {selectedSlot ? (
            <div className="space-y-4">
              <div className="rounded-xl border border-foreground/5 bg-muted/30 p-3 text-xs space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Topic:</span>
                  <span className="max-w-[12rem] text-right font-semibold">{selectedSlot.planned_topic || "Open questions"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Room:</span>
                  <span className="font-semibold">{selectedSlot.room || "—"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Duration:</span>
                  <span className="font-semibold">{selectedSlot.slot_minutes} minutes</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Status:</span>
                  <span className="font-semibold capitalize">{selectedSlot.status}</span>
                </div>
              </div>

              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">Booked Students</h4>
                {slotBookings.length > 0 ? (
                  <div className="space-y-2">
                    {slotBookings.map((booking) => {
                      const isActive = booking.status === "booked";
                      return (
                        <div key={booking.id} className="rounded-xl border border-foreground/8 bg-surface p-3 space-y-2">
                          <div className="flex justify-between items-start">
                            <div>
                              <p className="font-bold text-sm">{booking.student_name}</p>
                              <p className="text-[10px] text-muted-foreground">
                                Booked on {formatDate(booking.created_at)}
                              </p>
                            </div>
                            <span className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[9px] font-bold uppercase ${
                              booking.status === "booked"
                                ? "bg-blue-50 text-blue-700 border border-blue-200"
                                : booking.status === "completed"
                                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                : booking.status === "no_show"
                                ? "bg-rose-50 text-rose-700 border border-rose-200"
                                : "bg-muted text-muted-foreground border border-foreground/10"
                            }`}>
                              {booking.status.replace("_", " ")}
                            </span>
                          </div>

                          {booking.student_note && (
                            <div className="rounded bg-background p-2 text-[11px] leading-relaxed text-foreground/80">
                              <span className="font-semibold block text-muted-foreground text-[10px] uppercase mb-0.5">Student Note:</span>
                              {booking.student_note}
                            </div>
                          )}
                          {booking.student_topic_request && (
                            <div className="rounded bg-background p-2 text-[11px] leading-relaxed text-foreground/80">
                              <span className="font-semibold block text-muted-foreground text-[10px] uppercase mb-0.5">Requested Topic:</span>
                              {booking.student_topic_request}
                            </div>
                          )}

                          {isActive && (
                            <div className="flex gap-2 pt-1 border-t border-foreground/5 mt-1">
                              <button
                                type="button"
                                onClick={() => handleUpdateBookingStatus(booking.id, "completed")}
                                className="inline-flex items-center gap-1 rounded bg-emerald-50 border border-emerald-200 px-2 py-1 text-[10px] font-bold text-emerald-700 hover:bg-emerald-100"
                              >
                                <Check className="h-3 w-3" /> Mark Completed
                              </button>
                              <button
                                type="button"
                                onClick={() => handleUpdateBookingStatus(booking.id, "no_show")}
                                className="inline-flex items-center gap-1 rounded bg-rose-50 border border-rose-200 px-2 py-1 text-[10px] font-bold text-rose-700 hover:bg-rose-100"
                              >
                                <X className="h-3 w-3" /> No-Show
                              </button>
                              <button
                                type="button"
                                onClick={() => handleUpdateBookingStatus(booking.id, "cancelled")}
                                className="ml-auto text-[10px] font-bold text-destructive hover:underline"
                              >
                                Cancel
                              </button>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="rounded-lg border border-dashed border-foreground/15 bg-background py-8 text-center text-xs text-muted-foreground">
                    No bookings for this availability slot yet.
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="py-12 text-center text-sm text-muted-foreground">
              Select a slot from the table to view details.
            </div>
          )}
        </ChartCard>
      </div>

      {/* Create Availability Modal */}
      {createOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-4" onClick={() => setCreateOpen(false)} role="presentation">
          <div className="flex max-h-[90dvh] w-full max-w-md flex-col overflow-hidden rounded-2xl bg-surface shadow-card-hover animate-in fade-in zoom-in-95 duration-150 motion-reduce:animate-none" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="create-office-hours-title">
            <div className="flex shrink-0 items-center justify-between border-b border-foreground/5 px-5 py-3">
              <h3 id="create-office-hours-title" className="text-sm font-bold">Create Office Hour Availability</h3>
              <button type="button" onClick={() => setCreateOpen(false)} className="flex h-11 w-11 items-center justify-center rounded-lg hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40" aria-label="Close availability dialog">
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleCreateAvailability} className="min-h-0 flex-1 overflow-y-auto">
              <div className="space-y-4 px-5 py-4">
                {errorMsg && (
                  <div className="flex gap-2 rounded-lg bg-destructive/10 p-3 text-xs font-semibold text-destructive">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    <span>{errorMsg}</span>
                  </div>
                )}

                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Subject</span>
                  <select
                    value={newSubjectId}
                    onChange={(e) => {
                      setNewSubjectId(e.target.value);
                      setNewTeacherId("");
                    }}
                    required
                    className="w-full rounded-xl border border-foreground/10 bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
                  >
                    <option value="">Select Subject</option>
                    {subjects.map((s) => (
                      <option key={s.id} value={String(s.id)}>{s.name}</option>
                    ))}
                  </select>
                </label>

                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Teacher</span>
                  <select
                    value={newTeacherId}
                    onChange={(e) => setNewTeacherId(e.target.value)}
                    required
                    disabled={!newSubjectId}
                    className="w-full rounded-xl border border-foreground/10 bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
                  >
                    <option value="">{newSubjectId ? "Select Teacher" : "Select subject first"}</option>
                    {teachersForNewSubject.map((t) => (
                      <option key={t.id} value={String(t.id)}>{t.full_name}</option>
                    ))}
                  </select>
                  {newSubjectId && teachersForNewSubject.length === 0 ? (
                    <span className="mt-1 block text-[11px] font-semibold text-destructive">
                      No teachers are assigned to groups for this subject yet.
                    </span>
                  ) : null}
                </label>

                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Planned Topic</span>
                  <input
                    type="text"
                    value={newPlannedTopic}
                    onChange={(e) => setNewPlannedTopic(e.target.value)}
                    placeholder="e.g. Trigonometry revision, exam questions, open Q&A"
                    className="w-full rounded-xl border border-foreground/10 bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
                  />
                </label>

                <div className="grid grid-cols-2 gap-3">
                  <label className="block">
                    <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Session Date</span>
                    <input
                      type="date"
                      value={newSessionDate}
                      onChange={(e) => setNewSessionDate(e.target.value)}
                      required
                      className="w-full rounded-xl border border-foreground/10 bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
                    />
                  </label>

                  <label className="block">
                    <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Start Time</span>
                    <input
                      type="time"
                      value={newStartTime}
                      onChange={(e) => setNewStartTime(e.target.value)}
                      required
                      className="w-full rounded-xl border border-foreground/10 bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
                    />
                  </label>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <label className="block col-span-2">
                    <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Slot Length (Minutes)</span>
                    <input
                      type="number"
                      value={newSlotMinutes}
                      onChange={(e) => setNewSlotMinutes(e.target.value)}
                      min="5"
                      required
                      className="w-full rounded-xl border border-foreground/10 bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
                    />
                  </label>

                  <label className="block">
                    <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Capacity</span>
                    <input
                      type="number"
                      value={newCapacity}
                      onChange={(e) => setNewCapacity(e.target.value)}
                      min="1"
                      required
                      className="w-full rounded-xl border border-foreground/10 bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
                    />
                  </label>
                </div>

                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Room / Location</span>
                  <input
                    type="text"
                    value={newRoom}
                    onChange={(e) => setNewRoom(e.target.value)}
                    placeholder="e.g. Room 304, Zoom link"
                    className="w-full rounded-xl border border-foreground/10 bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
                  />
                </label>
              </div>

              <div className="flex shrink-0 gap-2 border-t border-foreground/5 px-5 py-3">
                <button type="submit" className="rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-primary-foreground hover:bg-primary/95">
                  Create
                </button>
                <button type="button" onClick={() => setCreateOpen(false)} className="rounded-xl bg-muted px-5 py-2.5 text-sm font-bold text-muted-foreground hover:bg-foreground/10">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
