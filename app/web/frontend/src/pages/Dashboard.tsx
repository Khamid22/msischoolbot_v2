import { Suspense, lazy, useState } from "react";
import {
  Activity,
  BarChart3,
  BookOpen,
  Calendar,
  ChevronDown,
  GraduationCap,
  LogOut,
  MessageSquare,
  Target,
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
  const examAttempts = examChartData.length
    ? Object.keys(examChartData[0]).filter((key) => key !== "examName")
    : [];

  const [profileOpen, setProfileOpen] = useState(false);
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

  return (
    <TelegramLayout
      topbar={
        <Topbar
          backUrl={props.dashboardBackUrl}
          title="Academic Dashboard"
          rightContent={
            <div className="flex items-center gap-2">
              <div className="hidden text-right sm:block">
                <p className="text-xs font-bold leading-tight">{String(student.fullName || "")}</p>
                <p className="text-[10px] text-muted-foreground">{currentGroup}</p>
              </div>
              <div className="relative">
                <button
                  type="button"
                  onClick={() => {
                    setProfileOpen((current) => !current);
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
          setSubjectOpen(false);
        }}
      >
        {props.profileError ? <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">{props.profileError}</div> : null}
        {props.profileNotice ? <div className="rounded-xl border border-success/20 bg-success/10 px-4 py-3 text-sm">{props.profileNotice}</div> : null}

        <section className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-display text-lg font-bold sm:text-xl">{studentName}</h2>
          <div className="relative">
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                setSubjectOpen((current) => !current);
                setProfileOpen(false);
              }}
              className="flex items-center gap-1 rounded-full bg-surface px-3 py-1.5 text-xs font-semibold shadow-card hover:shadow-card-hover"
            >
              {props.currentSubjectShortName || props.currentSubjectName}
              <ChevronDown className="h-3.5 w-3.5" />
            </button>
            {subjectOpen ? (
              <nav className="absolute right-0 top-full z-50 mt-1 w-52 rounded-xl border border-foreground/5 bg-surface py-1 shadow-card-hover">
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
        </section>

        <ChartCard title="Program Completion" icon={<Target className="h-4 w-4 text-info" />}>
          <ProgressBar value={props.programCompletedRate || 0} className="mb-2" />
          <p className="text-xs text-muted-foreground">
            {props.programCompletedLessons || 0}/180 lessons completed ({props.programCompletedRate || 0}%)
          </p>
        </ChartCard>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard title="AAP" value={`${averageGrade}/9`} icon={<GraduationCap className="h-3.5 w-3.5" />} href={props.aapLessonsUrl} />
          <StatCard title="AR" value={`${props.attendanceRate || 0}%`} icon={<Calendar className="h-3.5 w-3.5" />} href={props.arLessonsUrl} />
          <StatCard title="EP" value={`${props.examPerformance || 0}/9`} icon={<BarChart3 className="h-3.5 w-3.5" />} />
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
                examAttempts={examAttempts}
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
