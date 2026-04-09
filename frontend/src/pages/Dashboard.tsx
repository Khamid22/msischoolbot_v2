import { useState } from "react";
import {
  Activity,
  BarChart3,
  BookOpen,
  Calendar,
  ChevronDown,
  GraduationCap,
  LogOut,
  RefreshCw,
  Target,
  Trophy,
  User,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartCard } from "@/components/ChartCard";
import { ProgressBar } from "@/components/ProgressBar";
import { StatCard } from "@/components/StatCard";
import { UserAvatar } from "@/components/Avatar";
import { TelegramLayout, Topbar } from "@/components/TelegramLayout";
import {
  buildAttendanceDonutData,
  buildExamChartData,
  buildHomeworkChartData,
  buildStudentDisplayName,
} from "@/lib/dashboard-data";

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
  aapLessonsUrl?: string;
  arLessonsUrl?: string;
  currentSubjectName?: string;
  currentSubjectShortName?: string;
  subjectSwitchOptions?: SubjectOption[];
  studentProfile?: StudentProfile;
  profileNotice?: string;
  profileError?: string;
  dashboardBackUrl?: string;
  refreshUrl?: string;
  lastUpdatedLabel?: string;
  csrfToken?: string;
  logoutUrl?: string;
  changePasswordUrl?: string;
}

const attendanceColors = [
  "var(--tg-theme-button-color, hsl(var(--primary)))",
  "var(--tg-theme-link-color, hsl(var(--info)))",
  "var(--tg-theme-hint-color, hsl(var(--muted-foreground)))",
];

const examSeriesColors = [
  "var(--tg-theme-button-color, hsl(var(--primary)))",
  "var(--tg-theme-link-color, hsl(var(--info)))",
  "var(--tg-theme-hint-color, hsl(var(--muted-foreground)))",
];

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
          subtitleContent={
            props.refreshUrl ? (
              <a
                href={props.refreshUrl}
                aria-label="Refresh dashboard"
                className="inline-flex min-w-0 items-center gap-1.5 rounded-full border border-foreground/10 bg-background/80 px-2 py-0.5 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              >
                <RefreshCw className="h-3 w-3 shrink-0" />
                <span className="truncate">{props.lastUpdatedLabel || "Last Update: --."}</span>
              </a>
            ) : (
              <p className="truncate text-xs text-muted-foreground">{props.lastUpdatedLabel || "Last Update: --."}</p>
            )
          }
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

        <div className="grid gap-4 lg:grid-cols-2">
          <ChartCard title="Attendance Rate" subtitle={`Total Sessions: ${attendanceTotal}`} icon={<Calendar className="h-4 w-4 text-success" />}>
            {attendanceData.length ? (
              <>
                <div className="relative h-52 sm:h-60">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={attendanceData} dataKey="value" nameKey="name" innerRadius={70} outerRadius={92} paddingAngle={2}>
                        {attendanceData.map((entry, index) => (
                          <Cell key={entry.name} fill={attendanceColors[index]} />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                    <div className="rounded-full bg-surface/90 px-4 py-2 text-center shadow-sm">
                      <strong className="block font-display text-2xl leading-none">{props.attendanceRate || 0}%</strong>
                      <span className="mt-1 block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Attendance</span>
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="rounded-lg border border-foreground/5 px-3 py-2">
                    <strong className="block font-display text-lg">{presentCount}</strong>
                    <span className="text-[10px] uppercase tracking-wide text-muted-foreground">Present</span>
                  </div>
                  <div className="rounded-lg border border-foreground/5 px-3 py-2">
                    <strong className="block font-display text-lg">{absentCount}</strong>
                    <span className="text-[10px] uppercase tracking-wide text-muted-foreground">Absent</span>
                  </div>
                  <div className="rounded-lg border border-foreground/5 bg-warning/20 px-3 py-2">
                    <strong className="block font-display text-lg">{justifiedCount}</strong>
                    <span className="text-[10px] uppercase tracking-wide text-muted-foreground">Justified</span>
                  </div>
                </div>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">No attendance records yet.</p>
            )}
          </ChartCard>

          <ChartCard title="Exam Performance" subtitle="Scores by test attempts" icon={<BarChart3 className="h-4 w-4 text-info" />}>
            {examChartData.length ? (
              <div className="h-56 sm:h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={examChartData} margin={{ top: 8, right: 6, left: -6, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--foreground) / 0.06)" />
                    <XAxis dataKey="examName" tick={{ fontSize: 11 }} />
                    <YAxis domain={[0, 9]} tick={{ fontSize: 11 }} width={30} tickMargin={4} />
                    <Tooltip />
                    <Legend />
                    {examAttempts.map((attempt, index) => (
                      <Bar
                        key={attempt}
                        dataKey={attempt}
                        fill={examSeriesColors[index % examSeriesColors.length]}
                        radius={[4, 4, 0, 0]}
                      />
                    ))}
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No exam results yet.</p>
            )}
          </ChartCard>
        </div>

        <ChartCard title="Homework Grades" icon={<Activity className="h-4 w-4 text-success" />}>
          {homeworkChartData.length ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={homeworkChartData} margin={{ top: 8, right: 6, left: -6, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--foreground) / 0.06)" />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                  <YAxis domain={[1, 9]} tick={{ fontSize: 11 }} width={30} tickMargin={4} />
                  <Tooltip />
                  <Area
                    type="monotone"
                    dataKey="score"
                    stroke="var(--tg-theme-button-color, hsl(var(--primary)))"
                    fill="var(--tg-theme-button-color, hsl(var(--primary)))"
                    fillOpacity={0.15}
                    strokeWidth={3}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No homework grades yet.</p>
          )}
        </ChartCard>
      </div>

      {profileModalOpen ? (
        <div className="tg-fixed-modal fixed inset-0 z-50 flex items-center justify-center bg-foreground/50">
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
        <div className="tg-fixed-modal fixed inset-0 z-50 flex items-center justify-center bg-foreground/50">
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
        <div className="tg-fixed-modal fixed inset-0 z-50 flex items-center justify-center bg-foreground/50">
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
