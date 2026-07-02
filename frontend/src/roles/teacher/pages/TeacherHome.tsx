import { useState, useEffect } from "react";
import { LogOut, Users, ClipboardList, CalendarDays, Clock, Plus, Trash, Check, X, AlertCircle } from "lucide-react";
import { routes } from "@/shared/lib/routes";
import { JSON_HEADERS, XHR_HEADERS } from "@/shared/lib/api";

// Read-only teacher workspace. All data is server-rendered (scoped to this
// teacher's assigned group); there are no edit controls or API calls here.

type TeacherInfo = {
  id: number;
  full_name: string;
  login: string;
  assigned_group: string;
  category: string;
  semester_stage: string;
};

type Lesson = {
  id: number;
  lessonNumber: string;
  topic: string;
  date: string;
  order: number;
};

type Enrollment = {
  enrollmentId: number;
  fullName: string;
  averageGrade: number;
  coins: number;
  attendance: Record<string, string>;
  homework: Record<string, number>;
  exams: Record<string, number>;
};

type GroupGradebook = {
  group: { id: number; name: string; code: string; schoolCode: string; subjectName: string };
  lessons: Lesson[];
  examLabels: string[];
  enrollments: Enrollment[];
};

type TeacherPageProps = {
  authLogin?: string;
  csrfToken?: string;
  teacher: TeacherInfo;
  groups: GroupGradebook[];
  subjectsOptions?: Array<{ id: number; name: string }>;
};

type Availability = {
  id: number;
  teacher_id: number;
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
  room?: string;
};

function attLabel(value: string) {
  if (value === "present") return "P";
  if (value === "absent") return "A";
  if (value === "justified") return "J";
  return "·";
}

function attCls(value: string) {
  if (value === "present") return "bg-emerald-500 text-white";
  if (value === "absent") return "bg-red-500 text-white";
  if (value === "justified") return "bg-amber-400 text-white";
  return "text-foreground/20";
}

function GroupGradebookCard({ group }: { group: GroupGradebook }) {
  const lessons = group.lessons;
  const enrollments = group.enrollments;
  return (
    <div className="overflow-hidden rounded-xl border border-foreground/8 bg-surface shadow-card">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-foreground/8 px-4 py-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-bold">{group.group.name}</p>
          <p className="truncate text-xs text-muted-foreground">{group.group.subjectName}</p>
        </div>
        <span className="rounded-md bg-muted px-2.5 py-1 text-[11px] font-bold text-muted-foreground">
          {enrollments.length} students
        </span>
      </div>

      {enrollments.length === 0 ? (
        <div className="p-6 text-center text-sm text-muted-foreground">No students in this group yet.</div>
      ) : lessons.length === 0 ? (
        <div className="p-6 text-center text-sm text-muted-foreground">No lessons recorded yet.</div>
      ) : (
        <div className="miniapp-table-scroll max-h-[70dvh]">
          <table className="min-w-full border-collapse text-left text-xs">
            <thead className="sticky top-0 z-30">
              <tr className="bg-surface shadow-[0_1px_0_hsl(var(--foreground)/0.08)]">
                <th className="sticky left-0 z-40 min-w-[160px] border-b border-r border-foreground/10 bg-surface px-3 py-2 font-bold uppercase tracking-wide text-muted-foreground shadow-[1px_0_0_hsl(var(--foreground)/0.08)]">
                  Student
                </th>
                <th className="sticky left-[160px] z-40 min-w-[44px] border-b border-r border-foreground/10 bg-surface px-2 py-2 text-center font-bold uppercase tracking-wide text-muted-foreground shadow-[1px_0_0_hsl(var(--foreground)/0.08)]">
                  AAP
                </th>
                {lessons.map((lesson) => (
                  <th key={lesson.id} colSpan={2} className="min-w-[96px] border-l border-foreground/10 px-2 py-2 text-center align-top">
                    <span className="block whitespace-nowrap text-[10px] font-semibold text-muted-foreground">
                      {lesson.date || lesson.lessonNumber}
                    </span>
                    <span className="mt-0.5 block whitespace-normal break-words text-[9px] font-normal italic leading-tight text-muted-foreground/70">
                      {lesson.topic || "—"}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-foreground/5 bg-surface">
              {enrollments.map((en) => (
                <tr key={en.enrollmentId} className="hover:bg-foreground/[0.015]">
                  <td className="sticky left-0 z-20 border-r border-foreground/8 bg-surface px-3 py-1.5 text-sm font-semibold shadow-[1px_0_0_hsl(var(--foreground)/0.08)]">
                    {en.fullName}
                  </td>
                  <td className="sticky left-[160px] z-20 border-r border-foreground/8 bg-surface px-2 py-1.5 text-center font-bold text-muted-foreground shadow-[1px_0_0_hsl(var(--foreground)/0.08)]">
                    {en.averageGrade > 0 ? en.averageGrade.toFixed(0) : "–"}
                  </td>
                  {lessons.map((lesson) => {
                    const att = en.attendance[lesson.lessonNumber] || "";
                    const hw = en.homework[lesson.lessonNumber];
                    return (
                      <>
                        <td key={`${lesson.id}-att`} className="border-l border-foreground/5 px-1 py-1 text-center">
                          <span className={`inline-flex h-6 w-7 items-center justify-center rounded text-[10px] font-bold ${attCls(att)}`}>
                            {attLabel(att)}
                          </span>
                        </td>
                        <td key={`${lesson.id}-hw`} className="border-r border-foreground/5 px-1 py-1 text-center">
                          <span className={`text-[11px] ${hw !== undefined ? "font-bold text-blue-600" : "text-foreground/20"}`}>
                            {hw !== undefined ? hw : "·"}
                          </span>
                        </td>
                      </>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function TeacherHome(props: TeacherPageProps) {
  const teacher = props.teacher;
  const groups = Array.isArray(props.groups) ? props.groups : [];

  const [activeTab, setActiveTab] = useState<"gradebook" | "office_hours">("gradebook");
  const [availabilities, setAvailabilities] = useState<Availability[]>([]);
  const [bookings, setBookings] = useState<Booking[]>([]);

  // Create availability modal state
  const [createOpen, setCreateOpen] = useState(false);
  const [newSubjectId, setNewSubjectId] = useState("");
  const [newPlannedTopic, setNewPlannedTopic] = useState("");
  const [newStartsAt, setNewStartsAt] = useState("");
  const [newEndsAt, setNewEndsAt] = useState("");
  const [newSlotMinutes, setNewSlotMinutes] = useState("30");
  const [newRoom, setNewRoom] = useState("");
  const [newCapacity, setNewCapacity] = useState("1");
  const [errorMsg, setErrorMsg] = useState("");

  const fetchAvailabilities = async () => {
    try {
      const res = await fetch("/teacher/api/office-hours/availability", {
        headers: XHR_HEADERS
      });
      if (res.ok) {
        const data = await res.json();
        setAvailabilities(data.availabilities || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchBookings = async () => {
    try {
      const res = await fetch("/teacher/api/office-hours/bookings", {
        headers: XHR_HEADERS
      });
      if (res.ok) {
        const data = await res.json();
        setBookings(data.bookings || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (activeTab === "office_hours") {
      fetchAvailabilities();
      fetchBookings();
    }
  }, [activeTab]);

  const handleCreateAvailability = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");

    if (!newStartsAt || !newEndsAt) {
      setErrorMsg("Please fill in starts and ends times.");
      return;
    }

    try {
      const res = await fetch("/teacher/api/office-hours/availability", {
        method: "POST",
        headers: JSON_HEADERS,
        body: JSON.stringify({
          subject_id: newSubjectId ? Number(newSubjectId) : null,
          planned_topic: newPlannedTopic,
          starts_at: newStartsAt,
          ends_at: newEndsAt,
          slot_minutes: Number(newSlotMinutes),
          room: newRoom,
          capacity: Number(newCapacity),
          csrf_token: props.csrfToken || ""
        })
      });

      const data = await res.json();
      if (res.ok && data.ok) {
        setCreateOpen(false);
        // Reset form
        setNewSubjectId("");
        setNewPlannedTopic("");
        setNewStartsAt("");
        setNewEndsAt("");
        setNewRoom("");
        setNewCapacity("1");
        fetchAvailabilities();
      } else {
        setErrorMsg(data.message || "Failed to create availability.");
      }
    } catch (err) {
      setErrorMsg("Network error. Please try again.");
    }
  };

  const handleCancelSlot = async (id: number) => {
    if (!confirm("Are you sure you want to cancel this availability slot? All bookings for it will also be cancelled.")) return;
    try {
      const res = await fetch(`/teacher/api/office-hours/availability/${id}`, {
        method: "PATCH",
        headers: JSON_HEADERS,
        body: JSON.stringify({
          status: "cancelled",
          csrf_token: props.csrfToken || ""
        })
      });
      if (res.ok) {
        fetchAvailabilities();
        fetchBookings();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleUpdateBookingStatus = async (bookingId: number, status: string) => {
    try {
      const res = await fetch(`/teacher/api/office-hours/bookings/${bookingId}`, {
        method: "PATCH",
        headers: JSON_HEADERS,
        body: JSON.stringify({
          status,
          csrf_token: props.csrfToken || ""
        })
      });
      if (res.ok) {
        fetchBookings();
        fetchAvailabilities();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const formatDate = (isoStr: string) => {
    const d = new Date(isoStr);
    return d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
  };

  const formatTime = (isoStr: string) => {
    const d = new Date(isoStr);
    return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="app-min-height bg-background">
      <header
        className="sticky top-0 z-40 border-b border-foreground/8 bg-surface/95 backdrop-blur"
        style={{ paddingTop: "var(--app-top-inset)" }}
      >
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-3 px-3 py-3 sm:px-4">
          <div className="flex min-w-0 items-center gap-2.5">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary font-bold text-primary-foreground">
              {(teacher.full_name || "T").slice(0, 1).toUpperCase()}
            </div>
            <div className="min-w-0 leading-tight">
              <p className="truncate text-sm font-bold">{teacher.full_name || "Teacher"}</p>
              <p className="truncate text-[11px] text-muted-foreground">
                {teacher.login}
                {teacher.assigned_group ? ` · ${teacher.assigned_group}` : ""}
              </p>
            </div>
          </div>
          <form action={routes.logout} method="post" className="shrink-0">
            <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
            <button
              type="submit"
              className="flex h-9 items-center gap-1.5 rounded-lg px-3 text-xs font-bold text-destructive hover:bg-muted"
              aria-label="Log out"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Log out</span>
            </button>
          </form>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl space-y-4 px-3 py-4 sm:px-4">
        <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-xl border border-foreground/8 bg-surface p-3">
            <span className="block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Group</span>
            <span className="mt-1 block truncate text-sm font-bold">{teacher.assigned_group || "—"}</span>
          </div>
          <div className="rounded-xl border border-foreground/8 bg-surface p-3">
            <span className="block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Login</span>
            <span className="mt-1 block truncate text-sm font-bold">{teacher.login || "—"}</span>
          </div>
          <div className="rounded-xl border border-foreground/8 bg-surface p-3">
            <span className="block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Category</span>
            <span className="mt-1 block truncate text-sm font-bold capitalize">{(teacher.category || "—").replace(/_/g, " ")}</span>
          </div>
          <div className="rounded-xl border border-foreground/8 bg-surface p-3">
            <span className="block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Semester</span>
            <span className="mt-1 block truncate text-sm font-bold">{teacher.semester_stage || "—"}</span>
          </div>
        </section>

        {/* Tab Switcher */}
        <div className="flex border-b border-foreground/8">
          <button
            type="button"
            onClick={() => setActiveTab("gradebook")}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-bold border-b-2 transition-all active:scale-[0.98] duration-150 motion-reduce:active:scale-100 ${
              activeTab === "gradebook"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <ClipboardList className="h-4 w-4" />
            Gradebook
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("office_hours")}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-bold border-b-2 transition-all active:scale-[0.98] duration-150 motion-reduce:active:scale-100 ${
              activeTab === "office_hours"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <CalendarDays className="h-4 w-4" />
            Office Hours
          </button>
        </div>

        {activeTab === "gradebook" ? (
          <>
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-muted-foreground">
              <ClipboardList className="h-4 w-4" />
              My groups
            </div>

            {groups.length === 0 ? (
              <div className="rounded-xl border border-foreground/8 bg-surface p-8 text-center">
                <Users className="mx-auto mb-2 h-6 w-6 text-muted-foreground" />
                <p className="text-sm font-semibold">No group assigned yet</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Once you are assigned to a group, your students and gradebook appear here.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {groups.map((group) => (
                  <GroupGradebookCard key={group.group.id} group={group} />
                ))}
              </div>
            )}
          </>
        ) : (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-muted-foreground">
                <CalendarDays className="h-4 w-4" />
                My Office Hours
              </div>
              <button
                type="button"
                onClick={() => setCreateOpen(true)}
                className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-bold text-primary-foreground hover:bg-primary/95 shadow-sm"
              >
                <Plus className="h-3.5 w-3.5" />
                Create Availability
              </button>
            </div>

            {/* Upcoming Bookings Table */}
            <div className="rounded-xl border border-foreground/8 bg-surface overflow-hidden shadow-card">
              <div className="border-b border-foreground/8 px-4 py-3 bg-surface/50">
                <h3 className="text-xs font-bold uppercase tracking-wider text-foreground">Upcoming Bookings</h3>
              </div>
              <div className="miniapp-table-scroll">
                <table className="min-w-full border-collapse text-left text-xs">
                  <thead>
                    <tr className="bg-muted/30 border-b border-foreground/8">
                      <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Student</th>
                      <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Subject</th>
                      <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Date</th>
                      <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Time</th>
                      <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Room</th>
                      <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Status</th>
                      <th className="px-4 py-2.5 text-right font-bold uppercase text-muted-foreground">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-foreground/5">
                    {bookings.map((booking) => {
                      const isActive = booking.status === "booked";
                      return (
                        <tr key={booking.id} className="hover:bg-foreground/[0.015]">
                          <td className="px-4 py-3 font-semibold text-sm">
                            <div>
                              <div>{booking.student_name}</div>
                              {booking.student_note && (
                                <div className="mt-1 text-[11px] text-muted-foreground max-w-xs truncate" title={booking.student_note}>
                                  Note: {booking.student_note}
                                </div>
                              )}
                              {booking.student_topic_request && (
                                <div className="mt-1 max-w-xs truncate text-[11px] font-semibold text-foreground" title={booking.student_topic_request}>
                                  Topic request: {booking.student_topic_request}
                                </div>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-muted-foreground">{booking.subject_name || "—"}</td>
                          <td className="px-4 py-3">{formatDate(booking.starts_at)}</td>
                          <td className="px-4 py-3">
                            {formatTime(booking.starts_at)} - {formatTime(booking.ends_at)}
                          </td>
                          <td className="px-4 py-3">{booking.room || "—"}</td>
                          <td className="px-4 py-3">
                            <span className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-bold uppercase ${
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
                          </td>
                          <td className="px-4 py-3 text-right">
                            {isActive && (
                              <div className="flex justify-end gap-1.5">
                                <button
                                  type="button"
                                  onClick={() => handleUpdateBookingStatus(booking.id, "completed")}
                                  className="inline-flex h-7 items-center gap-1 rounded bg-emerald-50 border border-emerald-200 px-2 text-[10px] font-bold text-emerald-700 hover:bg-emerald-100"
                                >
                                  <Check className="h-3 w-3" /> Done
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleUpdateBookingStatus(booking.id, "no_show")}
                                  className="inline-flex h-7 items-center gap-1 rounded bg-rose-50 border border-rose-200 px-2 text-[10px] font-bold text-rose-700 hover:bg-rose-100"
                                >
                                  <X className="h-3 w-3" /> No-Show
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleUpdateBookingStatus(booking.id, "cancelled")}
                                  className="inline-flex h-7 items-center rounded border border-foreground/10 px-2 text-[10px] font-bold text-destructive hover:bg-destructive/5"
                                >
                                  Cancel
                                </button>
                              </div>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                    {bookings.length === 0 && (
                      <tr>
                        <td colSpan={7} className="p-8 text-center text-sm text-muted-foreground">
                          No upcoming bookings.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* My Availability Table */}
            <div className="rounded-xl border border-foreground/8 bg-surface overflow-hidden shadow-card">
              <div className="border-b border-foreground/8 px-4 py-3 bg-surface/50">
                <h3 className="text-xs font-bold uppercase tracking-wider text-foreground">My Availability</h3>
              </div>
              <div className="miniapp-table-scroll">
                <table className="min-w-full border-collapse text-left text-xs">
                  <thead>
                    <tr className="bg-muted/30 border-b border-foreground/8">
                      <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Day/Date</th>
                      <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Topic</th>
                      <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Time Range</th>
                      <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Slot Length</th>
                      <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Room</th>
                      <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Capacity</th>
                      <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Status</th>
                      <th className="px-4 py-2.5 text-right font-bold uppercase text-muted-foreground">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-foreground/5">
                    {availabilities.map((slot) => {
                      const isCancelled = slot.status === "cancelled";
                      return (
                        <tr key={slot.id} className="hover:bg-foreground/[0.015]">
                          <td className="px-4 py-3">{formatDate(slot.starts_at)}</td>
                          <td className="max-w-[14rem] truncate px-4 py-3 text-muted-foreground" title={slot.planned_topic || ""}>
                            {slot.planned_topic || "Open questions"}
                          </td>
                          <td className="px-4 py-3">
                            {formatTime(slot.starts_at)} - {formatTime(slot.ends_at)}
                          </td>
                          <td className="px-4 py-3">{slot.slot_minutes} min</td>
                          <td className="px-4 py-3">{slot.room || "—"}</td>
                          <td className="px-4 py-3 font-semibold">{slot.booked_count} / {slot.capacity}</td>
                          <td className="px-4 py-3">
                            <span className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-bold uppercase ${
                              isCancelled ? "bg-muted text-muted-foreground border border-foreground/10" : "bg-emerald-50 text-emerald-700 border border-emerald-200"
                            }`}>
                              {slot.status}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right">
                            {!isCancelled && (
                              <button
                                type="button"
                                onClick={() => handleCancelSlot(slot.id)}
                                className="inline-flex h-7 items-center gap-1 rounded bg-destructive/5 border border-destructive/10 px-2 text-[10px] font-bold text-destructive hover:bg-destructive/10"
                              >
                                <Trash className="h-3 w-3" /> Cancel
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                    {availabilities.length === 0 && (
                      <tr>
                        <td colSpan={8} className="p-8 text-center text-sm text-muted-foreground">
                          No availability slots created.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Create Availability Modal */}
      {createOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-4" onClick={() => setCreateOpen(false)}>
          <div className="flex max-h-[90dvh] w-full max-w-md flex-col overflow-hidden rounded-2xl bg-surface shadow-card-hover animate-in fade-in zoom-in-95 duration-150 motion-reduce:animate-none" onClick={(e) => e.stopPropagation()}>
            <div className="flex shrink-0 items-center justify-between border-b border-foreground/5 px-5 py-3">
              <h3 className="text-sm font-bold">Create Office Hour Availability</h3>
              <button type="button" onClick={() => setCreateOpen(false)} className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted">
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
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Subject (Optional)</span>
                  <select
                    value={newSubjectId}
                    onChange={(e) => setNewSubjectId(e.target.value)}
                    className="w-full rounded-xl border border-foreground/10 bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
                  >
                    <option value="">Select Subject</option>
                    {(props.subjectsOptions || []).map((s) => (
                      <option key={s.id} value={String(s.id)}>{s.name}</option>
                    ))}
                  </select>
                </label>

                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Planned Topic</span>
                  <input
                    type="text"
                    value={newPlannedTopic}
                    onChange={(e) => setNewPlannedTopic(e.target.value)}
                    placeholder="e.g. Exam questions, homework review, open Q&A"
                    className="w-full rounded-xl border border-foreground/10 bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
                  />
                </label>

                <div className="grid grid-cols-2 gap-3">
                  <label className="block">
                    <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Starts At</span>
                    <input
                      type="datetime-local"
                      value={newStartsAt}
                      onChange={(e) => setNewStartsAt(e.target.value)}
                      required
                      className="w-full rounded-xl border border-foreground/10 bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
                    />
                  </label>

                  <label className="block">
                    <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Ends At</span>
                    <input
                      type="datetime-local"
                      value={newEndsAt}
                      onChange={(e) => setNewEndsAt(e.target.value)}
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
