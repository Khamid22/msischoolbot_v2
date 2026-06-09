import { Suspense, lazy, useState } from "react";
import {
  Activity,
  BarChart3,
  Bell,
  BookOpen,
  Calendar,
  ChevronDown,
  GraduationCap,
  LogOut,
  MessageSquare,
  Trophy,
  User,
} from "lucide-react";
import { ChartCard } from "@/components/ChartCard";
import { ProgressBar } from "@/components/ProgressBar";
import { StatCard } from "@/components/StatCard";
import { UserAvatar } from "@/components/Avatar";
import { TelegramLayout, Topbar } from "@/components/TelegramLayout";
import { useLazyVisible } from "@/hooks/useLazyVisible";
import {
  buildAttendanceDonutData,
  buildExamChartData,
  buildHomeworkChartData,
  buildStudentDisplayName,
} from "@/lib/dashboard-data";

const DashboardChartsSection = lazy(() => import("./dashboard/DashboardChartsSection"));

interface SubjectOption {
  subject: string;
  subject_short: string;
  group?: string;
  url: string;
  is_current?: boolean;
}

interface StudentProfile {
  photo_url?: string;
  group_name?: string;
  school_name?: string;
  teacher_name?: string;
  classmates?: string[];
  profile_description?: string;
}

interface StudentAnnouncement {
  id?: number | string;
  title?: string;
  body?: string;
  priority?: string;
  pinned?: boolean;
  publishedAt?: string;
}

interface DashboardPageProps {
  payload?: Record<string, unknown>;
  attendanceRate?: number;
  examPerformance?: number;
  programCompletedLessons?: number;
  programCompletedRate?: number;
  ratingBoardUrl?: string;
  resourcesUrl?: string;
  chatUrl?: string;
  aapLessonsUrl?: string;
  arLessonsUrl?: string;
  currentSubjectName?: string;
  currentSubjectShortName?: string;
  subjectSwitchOptions?: SubjectOption[];
  studentProfile?: StudentProfile;
  profileNotice?: string;
  profileError?: string;
  dashboardBackUrl?: string;
  showDashboardBack?: boolean;
  refreshUrl?: string;
  lastUpdatedLabel?: string;
  announcements?: StudentAnnouncement[];
  csrfToken?: string;
  logoutUrl?: string;
  changePasswordUrl?: string;
}

const modalInsetStyle = {
  paddingTop: "var(--app-top-inset)",
  paddingRight: "max(1rem, var(--app-right-inset))",
  paddingBottom: "var(--app-bottom-inset)",
  paddingLeft: "max(1rem, var(--app-left-inset))",
} as const;

export default function DashboardPage(props: DashboardPageProps) {
  const payload = props.payload || {};
  const student =
    payload.student && typeof payload.student === "object" ? (payload.student as Record<string, unknown>) : {};
  const attendanceRecord =
    payload.attendanceRecord && typeof payload.attendanceRecord === "object"
      ? (payload.attendanceRecord as Record<string, unknown>)
      : {};
  const subjectOptions = Array.isArray(props.subjectSwitchOptions) ? props.subjectSwitchOptions : [];
  const examChartData = buildExamChartData(payload);
  const homeworkChartData = buildHomeworkChartData(payload);
  const attendanceData = buildAttendanceDonutData(payload);

  const [profileOpen, setProfileOpen] = useState(false);
  const [announcementsOpen, setAnnouncementsOpen] = useState(false);
  const [subjectOpen, setSubjectOpen] = useState(false);
  const [profileModalOpen, setProfileModalOpen] = useState(false);
  const [logoutOpen, setLogoutOpen] = useState(false);
  const [passwordOpen, setPasswordOpen] = useState(false);
  const { ref: chartsRef, visible: chartsVisible } = useLazyVisible({ rootMargin: "180px" });

  const studentName = buildStudentDisplayName(student);
  const studentInitials = String(student.initials || "").trim() || "ST";
  const currentGroup = String(student.group || "").trim();
  const attendanceTotal = Number(attendanceRecord.totalCount || 0);
  const presentCount = Number(attendanceRecord.presentCount || 0);
  const absentCount = Number(attendanceRecord.absentCount || 0);
  const justifiedCount = Number(attendanceRecord.justifiedAbsentCount || 0);
  const coins = Number(payload.coins || 0);
  const averageGrade = Math.round(Number(payload.averageGrade || 0));
  const attendanceRate = Math.round(Number(props.attendanceRate || 0));
  const examPerformance = Math.round(Number(props.examPerformance || 0));
  const completionRate = Math.round(Number(props.programCompletedRate || 0));
  const announcements = Array.isArray(props.announcements) ? props.announcements : [];

  return (
    <TelegramLayout
      topbar={
        <Topbar
          backUrl={props.showDashboardBack ? props.dashboardBackUrl : undefined}
          title={studentName}
          subtitle={currentGroup || undefined}
          subtitleContent={
            <div className="flex min-w-0 items-center gap-2">
              {currentGroup ? <span className="truncate text-xs text-muted-foreground">{currentGroup}</span> : null}
              <div className="relative min-w-0">
                {subjectOptions.length > 1 ? (
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      setSubjectOpen((current) => !current);
                      setProfileOpen(false);
                      setAnnouncementsOpen(false);
                    }}
                    className="flex max-w-[11rem] items-center gap-1 rounded-full bg-muted px-2.5 py-1 text-[11px] font-bold hover:bg-foreground/10 sm:max-w-xs"
                  >
                    <span className="truncate">{props.currentSubjectShortName || props.currentSubjectName}</span>
                    <ChevronDown className="h-3 w-3 shrink-0" />
                  </button>
                ) : (
                  <span className="block max-w-[11rem] truncate rounded-full bg-muted px-2.5 py-1 text-[11px] font-bold sm:max-w-xs">
                    {props.currentSubjectShortName || props.currentSubjectName}
                  </span>
                )}
                {subjectOpen ? (
                  <nav className="absolute left-0 top-full z-50 mt-1 w-52 rounded-xl border border-foreground/5 bg-surface py-1 shadow-card-hover">
                    {subjectOptions.map((option) => (
                      <a
                        key={`${option.subject}-${option.group}`}
                        href={option.url}
                        className={`flex items-center justify-between gap-3 px-4 py-2.5 text-xs font-medium hover:bg-muted ${
                          option.is_current ? "font-bold text-primary" : ""
                        }`}
                      >
                        <strong>{option.subject_short}</strong>
                        <span className="text-muted-foreground">{option.group}</span>
                      </a>
                    ))}
                  </nav>
                ) : null}
              </div>
            </div>
          }
          rightContent={
            <div className="flex items-center gap-2">
              <div className="relative">
                <button
                  type="button"
                  onClick={() => {
                    setAnnouncementsOpen((current) => !current);
                    setProfileOpen(false);
                    setSubjectOpen(false);
                  }}
                  className="relative flex h-8 w-8 items-center justify-center rounded-full bg-surface shadow-card hover:bg-muted"
                  aria-label="Announcements"
                >
                  <Bell className="h-4 w-4" />
                  {announcements.length ? (
                    <span className="absolute right-0.5 top-0.5 h-2 w-2 rounded-full bg-destructive ring-2 ring-surface" />
                  ) : null}
                </button>
                {announcementsOpen ? (
                  <div className="absolute right-0 top-full z-50 mt-1 w-72 overflow-hidden rounded-xl border border-foreground/5 bg-surface shadow-card-hover">
                    <div className="flex items-center justify-between border-b border-foreground/5 px-4 py-2.5">
                      <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Announcements</p>
                      {announcements.length ? <span className="text-[11px] font-bold text-muted-foreground">{announcements.length}</span> : null}
                    </div>
                    {announcements.length ? (
                      <div className="max-h-80 overflow-y-auto py-1">
                        {announcements.map((item, index) => (
                          <article key={String(item.id ?? `${item.title}-${index}`)} className="border-b border-foreground/5 px-4 py-3 last:border-b-0">
                            <div className="flex items-start justify-between gap-2">
                              <p className="min-w-0 text-sm font-bold leading-5">{item.title || "Announcement"}</p>
                              <span className={announcementBadgeClass(item.priority)}>{announcementPriorityLabel(item.priority)}</span>
                            </div>
                            {item.body ? <p className="mt-1 text-xs leading-5 text-muted-foreground">{item.body}</p> : null}
                          </article>
                        ))}
                      </div>
                    ) : (
                      <p className="px-4 py-6 text-center text-sm text-muted-foreground">No announcements yet.</p>
                    )}
                  </div>
                ) : null}
              </div>
              <div className="relative">
                <button
                  type="button"
                  onClick={() => {
                    setProfileOpen((current) => !current);
                    setAnnouncementsOpen(false);
                    setSubjectOpen(false);
                  }}
                  className="flex"
                >
                  <UserAvatar
                    initials={studentInitials}
                    src={String(props.studentProfile?.photo_url || "") || undefined}
                    size="sm"
                  />
                </button>
                {profileOpen ? (
                  <nav className="absolute right-0 top-full z-50 mt-1 w-44 rounded-xl border border-foreground/5 bg-surface py-1 shadow-card-hover">
                    <button
                      type="button"
                      onClick={() => {
                        setProfileOpen(false);
                        setProfileModalOpen(true);
                      }}
                      className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-xs font-medium hover:bg-muted"
                    >
                      <User className="h-3.5 w-3.5" />
                      Profile
                    </button>
                    <a href={props.ratingBoardUrl} className="flex items-center gap-2 px-4 py-2.5 text-xs font-medium hover:bg-muted">
                      <Trophy className="h-3.5 w-3.5" />
                      Rating
                    </a>
                    <a href={props.resourcesUrl} className="flex items-center gap-2 px-4 py-2.5 text-xs font-medium hover:bg-muted">
                      <BookOpen className="h-3.5 w-3.5" />
                      Resources
                    </a>
                    <a href={props.chatUrl} className="flex items-center gap-2 px-4 py-2.5 text-xs font-medium hover:bg-muted">
                      <MessageSquare className="h-3.5 w-3.5" />
                      Chat
                    </a>
                    <button
                      type="button"
                      onClick={() => {
                        setProfileOpen(false);
                        setLogoutOpen(true);
                      }}
                      className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-xs font-medium text-destructive hover:bg-muted"
                    >
                      <LogOut className="h-3.5 w-3.5" />
                      Logout
                    </button>
                  </nav>
                ) : null}
              </div>
            </div>
          }
        />
      }
    >
      <div
        className="space-y-4 pt-2 sm:pt-0"
        onClick={() => {
          setProfileOpen(false);
          setAnnouncementsOpen(false);
          setSubjectOpen(false);
        }}
      >
        {props.profileError ? <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">{props.profileError}</div> : null}
        {props.profileNotice ? <div className="rounded-xl border border-success/20 bg-success/10 px-4 py-3 text-sm">{props.profileNotice}</div> : null}

        <section className="rounded-xl border border-foreground/10 bg-surface p-4 shadow-card">
          <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
            <div className="min-w-0">
              <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Program Progress</p>
              <p className="mt-0.5 text-sm font-semibold">
                {props.programCompletedLessons || 0}/180 lessons completed
              </p>
            </div>
            <p className="font-display text-2xl font-bold">{completionRate}%</p>
          </div>
          <ProgressBar value={completionRate} />
        </section>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard title="AAP" value={`${averageGrade}/9`} icon={<GraduationCap className="h-3.5 w-3.5" />} href={props.aapLessonsUrl} />
          <StatCard title="AR" value={`${attendanceRate}%`} icon={<Calendar className="h-3.5 w-3.5" />} href={props.arLessonsUrl} />
          <StatCard title="EP" value={`${examPerformance}/9`} icon={<BarChart3 className="h-3.5 w-3.5" />} />
          <StatCard title="Coins" value={String(coins)} icon={<Activity className="h-3.5 w-3.5" />} />
        </div>

        <div ref={chartsRef} className="space-y-4">
          {chartsVisible ? (
            <Suspense fallback={<ChartsFallback />}>
              <DashboardChartsSection
                attendanceTotal={attendanceTotal}
                attendanceRate={props.attendanceRate || 0}
                presentCount={presentCount}
                absentCount={absentCount}
                justifiedCount={justifiedCount}
                attendanceData={attendanceData}
                examChartData={examChartData}
                homeworkChartData={homeworkChartData}
              />
            </Suspense>
          ) : (
            <ChartsFallback />
          )}
        </div>
      </div>

      {profileModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/50" style={modalInsetStyle}>
          <div className="max-h-full w-full max-w-md overflow-y-auto rounded-2xl bg-surface p-5 shadow-card-hover">
            <h3 className="font-display text-base font-bold">Profile</h3>
            <div className="mt-4 space-y-3">
              <div className="flex justify-center">
                <UserAvatar initials={studentInitials} src={String(props.studentProfile?.photo_url || "") || undefined} size="lg" />
              </div>
              {[
                ["Group", props.studentProfile?.group_name || "-"],
                ["School", props.studentProfile?.school_name || "-"],
                ["Teacher", props.studentProfile?.teacher_name || "-"],
              ].map(([label, value]) => (
                <div key={label} className="flex items-start justify-between gap-3 rounded-lg border border-foreground/5 px-3 py-2 text-sm">
                  <span className="text-muted-foreground">{label}</span>
                  <strong className="text-right">{value}</strong>
                </div>
              ))}
              {props.studentProfile?.classmates?.length ? (
                <div className="rounded-lg border border-foreground/5 px-3 py-2 text-sm">
                  <span className="block text-muted-foreground">Group mates</span>
                  <ul className="mt-2 list-disc space-y-1 pl-5">
                    {props.studentProfile.classmates.map((classmate) => (
                      <li key={classmate}>{classmate}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {props.studentProfile?.profile_description ? (
                <div className="rounded-lg border border-foreground/5 px-3 py-2 text-sm">
                  <span className="block text-muted-foreground">Description</span>
                  <p className="mt-2 leading-6">{props.studentProfile.profile_description}</p>
                </div>
              ) : null}
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  setProfileModalOpen(false);
                  setPasswordOpen(true);
                }}
                className="rounded-lg border-2 border-foreground/10 px-4 py-2 text-sm font-bold hover:bg-muted"
              >
                Change Password
              </button>
              <button
                type="button"
                onClick={() => setProfileModalOpen(false)}
                className="rounded-lg border-2 border-foreground/10 px-4 py-2 text-sm font-bold hover:bg-muted"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {logoutOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/50" style={modalInsetStyle}>
          <div className="max-h-full w-full max-w-sm overflow-y-auto rounded-2xl bg-surface p-5 shadow-card-hover">
            <h3 className="font-display text-base font-bold">Confirm Logout</h3>
            <p className="mt-2 text-sm text-muted-foreground">Are you sure you want to logout?</p>
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setLogoutOpen(false)}
                className="rounded-lg border-2 border-foreground/10 px-4 py-2 text-sm font-bold hover:bg-muted"
              >
                Cancel
              </button>
              <form action={props.logoutUrl} method="post">
                <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
                <button type="submit" className="rounded-lg bg-destructive px-4 py-2 text-sm font-bold text-destructive-foreground">
                  Logout
                </button>
              </form>
            </div>
          </div>
        </div>
      ) : null}

      {passwordOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/50" style={modalInsetStyle}>
          <div className="max-h-full w-full max-w-md overflow-y-auto rounded-2xl bg-surface p-5 shadow-card-hover">
            <h3 className="font-display text-base font-bold">Change Password</h3>
            <form action={props.changePasswordUrl} method="post" className="mt-4 space-y-4">
              <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
              <input type="hidden" name="student_id" value={String(student.id || "")} />
              <input type="hidden" name="subject" value={props.currentSubjectName || ""} />
              <input type="hidden" name="group" value={currentGroup} />
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Current Password</span>
                <input
                  type="password"
                  name="current_password"
                  autoComplete="current-password"
                  required
                  className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-3 text-sm outline-none focus:border-foreground/30"
                />
              </label>
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">New Password</span>
                <input
                  type="password"
                  name="new_password"
                  minLength={6}
                  autoComplete="new-password"
                  required
                  className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-3 text-sm outline-none focus:border-foreground/30"
                />
              </label>
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Confirm Password</span>
                <input
                  type="password"
                  name="confirm_password"
                  minLength={6}
                  autoComplete="new-password"
                  required
                  className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-3 text-sm outline-none focus:border-foreground/30"
                />
              </label>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setPasswordOpen(false)}
                  className="rounded-lg border-2 border-foreground/10 px-4 py-2 text-sm font-bold hover:bg-muted"
                >
                  Cancel
                </button>
                <button type="submit" className="rounded-lg bg-primary px-4 py-2 text-sm font-bold text-primary-foreground">
                  Save
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </TelegramLayout>
  );
}

function ChartsFallback() {
  return (
    <>
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Attendance Rate" subtitle="Loading chart data..." icon={<Calendar className="h-4 w-4 text-success" />}>
          <div className="h-52 animate-pulse rounded-lg bg-muted/70 sm:h-60" />
        </ChartCard>
        <ChartCard title="Exam Performance" subtitle="Loading chart data..." icon={<BarChart3 className="h-4 w-4 text-info" />}>
          <div className="h-56 animate-pulse rounded-lg bg-muted/70 sm:h-64" />
        </ChartCard>
      </div>
      <ChartCard title="Homework Grades" subtitle="Loading chart data..." icon={<Activity className="h-4 w-4 text-success" />}>
        <div className="h-64 animate-pulse rounded-lg bg-muted/70" />
      </ChartCard>
    </>
  );
}

function announcementPriorityLabel(priority?: string) {
  const normalized = String(priority || "").trim().toLowerCase();
  if (normalized === "urgent") return "Urgent";
  if (normalized === "important") return "Important";
  return "Info";
}

function announcementBadgeClass(priority?: string) {
  const normalized = String(priority || "").trim().toLowerCase();
  if (normalized === "urgent") {
    return "shrink-0 rounded-full border border-destructive/20 bg-destructive/5 px-2 py-0.5 text-[10px] font-bold text-destructive";
  }
  if (normalized === "important") {
    return "shrink-0 rounded-full border border-warning/30 bg-warning/15 px-2 py-0.5 text-[10px] font-bold text-foreground";
  }
  return "shrink-0 rounded-full border border-foreground/10 bg-muted px-2 py-0.5 text-[10px] font-bold text-muted-foreground";
}
