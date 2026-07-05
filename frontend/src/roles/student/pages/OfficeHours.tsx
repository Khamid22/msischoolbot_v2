import { useState, useEffect } from "react";
import { Calendar, Clock, MapPin, User, ChevronDown, Check, X, AlertCircle, Plus } from "lucide-react";
import { AdminEmbedLayout, isAdminEmbedMode, withEmbedMode } from "@/shared/ui/AdminEmbedLayout";
import { ChartCard } from "@/shared/ui/ChartCard";
import { TelegramLayout, Topbar } from "@/shared/ui/TelegramLayout";
import { JSON_HEADERS, XHR_HEADERS } from "@/shared/lib/api";
import { useDismissibleLayer } from "@/shared/lib/useDismissibleLayer";

type SubjectOption = {
  id: number;
  name: string;
};

type TeacherOption = {
  id: number;
  full_name: string;
};

type StudentProfile = {
  id: number;
  full_name: string;
  login: string;
  group: string;
  schoolCode: string;
  subject: string;
};

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
  room?: string;
  planned_topic?: string;
};

interface StudentOfficeHoursProps {
  backUrl?: string;
  currentStudent?: StudentProfile;
  subjects?: SubjectOption[];
  teachers?: TeacherOption[];
  csrfToken?: string;
  embedMode?: string;
}

export default function StudentOfficeHours(props: StudentOfficeHoursProps) {
  const currentStudent = props.currentStudent;
  const subjects = Array.isArray(props.subjects) ? props.subjects : [];
  const teachers = Array.isArray(props.teachers) ? props.teachers : [];
  const isAdminEmbed = isAdminEmbedMode(props.embedMode);
  const subjectOptions = subjects.filter((subject) => Number(subject.id) > 0);
  const enrolledSubjectIds = new Set(subjectOptions.map((subject) => Number(subject.id)));
  const enrolledSubjectNames = new Set(subjects.map((subject) => subject.name.trim().toLowerCase()).filter(Boolean));

  // States
  const [availabilities, setAvailabilities] = useState<Availability[]>([]);
  const [myBookings, setMyBookings] = useState<Booking[]>([]);

  // Filter States
  const [subjectFilter, setSubjectFilter] = useState<string>("all");
  const [teacherFilter, setTeacherFilter] = useState<string>("all");
  const [dateFilter, setDateFilter] = useState<string>("");

  // Modal / Booking States
  const [bookingSlot, setBookingSlot] = useState<Availability | null>(null);
  useDismissibleLayer({
    enabled: Boolean(bookingSlot),
    onDismiss: () => setBookingSlot(null),
    dismissOnOutsidePointer: false,
  });
  const [studentTopicRequest, setStudentTopicRequest] = useState<string>("");
  const [studentNote, setStudentNote] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string>("");
  const [successMsg, setSuccessMsg] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  useEffect(() => {
    fetchMyBookings();
  }, []);

  useEffect(() => {
    fetchAvailabilities();
  }, [subjectFilter, teacherFilter, dateFilter]);

  const fetchAvailabilities = async () => {
    try {
      const params = new URLSearchParams();
      if (teacherFilter !== "all") params.set("teacher_id", teacherFilter);
      if (subjectFilter !== "all") params.set("subject_id", subjectFilter);
      if (dateFilter) {
        // Starts at from selected date at 00:00
        const d = new Date(dateFilter);
        params.set("starts_at_from", d.toISOString());
      } else {
        // Default starts_at_from to current time
        params.set("starts_at_from", new Date().toISOString());
      }

      const res = await fetch(`/api/office-hours/availability?${params.toString()}`, {
        headers: XHR_HEADERS
      });
      if (res.ok) {
        const data = await res.json();
        setAvailabilities(data.availabilities || []);
      }
    } catch (e) {
      console.error("Failed to fetch office hours availabilities", e);
    }
  };

  const fetchMyBookings = async () => {
    try {
      const res = await fetch("/api/office-hours/bookings", {
        headers: XHR_HEADERS
      });
      if (res.ok) {
        const data = await res.json();
        setMyBookings(data.bookings || []);
      }
    } catch (e) {
      console.error("Failed to fetch my bookings", e);
    }
  };

  const handleBookSlot = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!bookingSlot) return;

    setErrorMsg("");
    setSuccessMsg("");
    setIsSubmitting(true);

    try {
      const res = await fetch("/api/office-hours/bookings", {
        method: "POST",
        headers: JSON_HEADERS,
        body: JSON.stringify({
          availability_id: bookingSlot.id,
          student_topic_request: studentTopicRequest,
          student_note: studentNote,
          csrf_token: props.csrfToken || ""
        })
      });

      const data = await res.json();
      if (res.ok && data.ok) {
        setSuccessMsg("Office hour session booked successfully!");
        setStudentTopicRequest("");
        setStudentNote("");
        setBookingSlot(null);
        fetchMyBookings();
        fetchAvailabilities();
      } else {
        setErrorMsg(data.message || "Failed to book office hour.");
      }
    } catch (err) {
      setErrorMsg("Network error. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancelBooking = async (bookingId: number) => {
    if (!confirm("Are you sure you want to cancel this booking?")) return;
    try {
      const res = await fetch(`/api/office-hours/bookings/${bookingId}`, {
        method: "PATCH",
        headers: JSON_HEADERS,
        body: JSON.stringify({
          status: "cancelled",
          csrf_token: props.csrfToken || ""
        })
      });
      const data = await res.json();
      if (res.ok && data.ok) {
        fetchMyBookings();
        fetchAvailabilities();
      } else {
        alert(data.message || "Failed to cancel booking.");
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

  const visibleAvailabilities = availabilities.filter((slot) => {
    if (!slot.subject_id && !slot.subject_name) return true;
    if (slot.subject_id && enrolledSubjectIds.size > 0) {
      return enrolledSubjectIds.has(Number(slot.subject_id));
    }
    const subjectName = String(slot.subject_name || "").trim().toLowerCase();
    return subjectName ? enrolledSubjectNames.has(subjectName) : true;
  });

  const content = (
    <div className="space-y-6">
      {successMsg && (
        <div className="flex gap-2 rounded-xl bg-emerald-50 border border-emerald-200 p-3 text-xs font-bold text-emerald-700">
          <Check className="h-4 w-4 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Filter Section */}
      <div className="rounded-xl border border-foreground/10 bg-surface p-4 shadow-card">
        <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3">Filters</h3>
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="block">
            <span className="mb-1 block text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Subject</span>
            <select
              value={subjectFilter}
              onChange={(e) => setSubjectFilter(e.target.value)}
              className="w-full rounded-lg border border-foreground/10 bg-background px-3 py-2 text-xs font-semibold outline-none focus:border-foreground/30"
            >
              <option value="all">All Subjects</option>
              {subjectOptions.map((s) => (
                <option key={s.id} value={String(s.id)}>{s.name}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="mb-1 block text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Teacher</span>
            <select
              value={teacherFilter}
              onChange={(e) => setTeacherFilter(e.target.value)}
              className="w-full rounded-lg border border-foreground/10 bg-background px-3 py-2 text-xs font-semibold outline-none focus:border-foreground/30"
            >
              <option value="all">All Teachers</option>
              {teachers.map((t) => (
                <option key={t.id} value={String(t.id)}>{t.full_name}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="mb-1 block text-[10px] font-bold uppercase tracking-wider text-muted-foreground">From Date</span>
            <input
              type="date"
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
              className="w-full rounded-lg border border-foreground/10 bg-background px-3 py-2 text-xs font-semibold outline-none focus:border-foreground/30"
            />
          </label>
        </div>
      </div>

      {/* Available Slots Section */}
      <ChartCard
        title="Available Office Hours"
        subtitle={`${visibleAvailabilities.length} available slots found`}
        icon={<Clock className="h-4 w-4 text-info" />}
      >
        <div className="miniapp-table-scroll rounded-lg border border-foreground/10">
          <table className="w-full text-left text-xs">
            <thead className="bg-surface shadow-[0_1px_0_hsl(var(--foreground)/0.08)]">
              <tr className="border-b border-foreground/5">
                <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Teacher</th>
                <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Subject</th>
                <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Topic</th>
                <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Date</th>
                <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Time</th>
                <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Room</th>
                <th className="px-4 py-2.5 text-center font-bold uppercase text-muted-foreground">Available Seats</th>
                <th className="px-4 py-2.5 text-right font-bold uppercase text-muted-foreground">Book</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-foreground/5 bg-background">
              {visibleAvailabilities.map((slot) => {
                const seatsLeft = slot.capacity - slot.booked_count;
                const isBookedOut = seatsLeft <= 0;
                return (
                  <tr key={slot.id} className="hover:bg-foreground/[0.015]">
                    <td className="px-4 py-3 font-semibold text-sm whitespace-nowrap">{slot.teacher_name}</td>
                    <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">{slot.subject_name || "—"}</td>
                    <td className="max-w-[14rem] truncate px-4 py-3 text-muted-foreground" title={slot.planned_topic || ""}>
                      {slot.planned_topic || "Open questions"}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">{formatDate(slot.starts_at)}</td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {formatTime(slot.starts_at)} - {formatTime(slot.ends_at)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">{slot.room || "—"}</td>
                    <td className="px-4 py-3 text-center font-bold whitespace-nowrap">
                      {isBookedOut ? (
                        <span className="text-destructive">Full</span>
                      ) : (
                        <span>{seatsLeft} / {slot.capacity}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      <button
                        type="button"
                        disabled={isBookedOut}
                        onClick={() => {
                          setBookingSlot(slot);
                          setErrorMsg("");
                        }}
                        className={`inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-bold transition-all ${
                          isBookedOut
                            ? "bg-muted text-muted-foreground cursor-not-allowed"
                            : "bg-primary text-primary-foreground hover:bg-primary/90"
                        }`}
                      >
                        Book
                      </button>
                    </td>
                  </tr>
                );
              })}
              {visibleAvailabilities.length === 0 && (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-sm text-muted-foreground">
                    No available office hours found matching filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </ChartCard>

      {/* My Bookings Section */}
      <ChartCard
        title="My Bookings"
        subtitle={`${myBookings.filter(b => b.status === 'booked').length} upcoming sessions`}
        icon={<Calendar className="h-4 w-4 text-info" />}
      >
        <div className="miniapp-table-scroll rounded-lg border border-foreground/10">
          <table className="w-full text-left text-xs">
            <thead className="bg-surface shadow-[0_1px_0_hsl(var(--foreground)/0.08)]">
              <tr className="border-b border-foreground/5">
                <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Teacher</th>
                <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Subject</th>
                <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Topic</th>
                <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Date</th>
                <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Time</th>
                <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Room</th>
                <th className="px-4 py-2.5 font-bold uppercase text-muted-foreground">Status</th>
                <th className="px-4 py-2.5 text-right font-bold uppercase text-muted-foreground">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-foreground/5 bg-background">
              {myBookings.map((booking) => {
                const isBooked = booking.status === "booked";
                return (
                  <tr key={booking.id} className="hover:bg-foreground/[0.015]">
                    <td className="px-4 py-3 font-semibold text-sm whitespace-nowrap">{booking.teacher_name}</td>
                    <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">{booking.subject_name || "—"}</td>
                    <td className="max-w-[14rem] truncate px-4 py-3 text-muted-foreground" title={booking.student_topic_request || booking.planned_topic || ""}>
                      {booking.student_topic_request || booking.planned_topic || "Open questions"}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">{formatDate(booking.starts_at)}</td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {formatTime(booking.starts_at)} - {formatTime(booking.ends_at)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">{booking.room || "—"}</td>
                    <td className="px-4 py-3 whitespace-nowrap">
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
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      {isBooked && (
                        <button
                          type="button"
                          onClick={() => handleCancelBooking(booking.id)}
                          className="inline-flex h-7 items-center rounded-lg border border-destructive/20 bg-destructive/5 px-2 text-[10px] font-bold text-destructive hover:bg-destructive/15"
                        >
                          Cancel Booking
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
              {myBookings.length === 0 && (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-sm text-muted-foreground">
                    You have not booked any office hour sessions yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </ChartCard>

      {/* Booking Confirmation Modal */}
      {bookingSlot && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-4" onClick={() => setBookingSlot(null)}>
          <div className="flex max-h-[90dvh] w-full max-w-md flex-col overflow-hidden rounded-2xl bg-surface shadow-card-hover animate-in fade-in zoom-in-95 duration-150 motion-reduce:animate-none" onClick={(e) => e.stopPropagation()}>
            <div className="flex shrink-0 items-center justify-between border-b border-foreground/5 px-5 py-3">
              <h3 className="text-sm font-bold">Book Office Hour Session</h3>
              <button type="button" onClick={() => setBookingSlot(null)} className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted">
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleBookSlot} className="min-h-0 flex-1 overflow-y-auto">
              <div className="space-y-4 px-5 py-4">
                {errorMsg && (
                  <div className="flex gap-2 rounded-lg bg-destructive/10 p-3 text-xs font-semibold text-destructive">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    <span>{errorMsg}</span>
                  </div>
                )}

                <div className="rounded-xl border border-foreground/5 bg-muted/30 p-3 text-xs space-y-2">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Teacher:</span>
                    <span className="font-semibold">{bookingSlot.teacher_name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Subject:</span>
                    <span className="font-semibold">{bookingSlot.subject_name || "—"}</span>
                  </div>
                  <div className="flex justify-between gap-3">
                    <span className="text-muted-foreground">Teacher Topic:</span>
                    <span className="text-right font-semibold">{bookingSlot.planned_topic || "Open questions"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Date:</span>
                    <span className="font-semibold">{formatDate(bookingSlot.starts_at)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Time:</span>
                    <span className="font-semibold">{formatTime(bookingSlot.starts_at)} - {formatTime(bookingSlot.ends_at)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Room:</span>
                    <span className="font-semibold">{bookingSlot.room || "—"}</span>
                  </div>
                </div>

                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Topic You Want Covered</span>
                  <input
                    type="text"
                    value={studentTopicRequest}
                    onChange={(e) => setStudentTopicRequest(e.target.value)}
                    placeholder="e.g. I want to review simultaneous equations"
                    className="w-full rounded-xl border border-foreground/10 bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
                  />
                </label>

                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Extra Notes (Optional)</span>
                  <textarea
                    value={studentNote}
                    onChange={(e) => setStudentNote(e.target.value)}
                    placeholder="Describe what you would like to discuss (e.g. review homework 3, exam preparation)"
                    rows={3}
                    className="w-full rounded-xl border border-foreground/10 bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30 resize-none"
                  />
                </label>
              </div>

              <div className="flex shrink-0 gap-2 border-t border-foreground/5 px-5 py-3">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-primary-foreground hover:bg-primary/95"
                >
                  {isSubmitting ? "Booking..." : "Confirm Booking"}
                </button>
                <button type="button" onClick={() => setBookingSlot(null)} className="rounded-xl bg-muted px-5 py-2.5 text-sm font-bold text-muted-foreground hover:bg-foreground/10">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );

  if (isAdminEmbed) {
    return (
      <AdminEmbedLayout
        title="Book Office Hour"
        subtitle={currentStudent?.full_name || "Student"}
        backUrl={props.backUrl}
        badge="Office Hours"
      >
        {content}
      </AdminEmbedLayout>
    );
  }

  return (
    <TelegramLayout
      topbar={
        <Topbar
          backUrl={props.backUrl}
          title="Book Office Hour"
        />
      }
    >
      <div className="animate-in">{content}</div>
    </TelegramLayout>
  );
}
