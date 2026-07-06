// Recharts-based analytics for the Active Teacher cabinet. Loaded lazily so
// the Telegram Mini App first paint (and the academy cabinet, which never
// needs recharts) stays light.
import { useMemo } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

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
  attendance: Record<string, string>;
  homework: Record<string, number>;
};

type GroupGradebook = {
  group: { id: number; name: string; subjectName: string };
  lessons: Lesson[];
  enrollments: Enrollment[];
};

function attendanceTrendRows(groups: GroupGradebook[]) {
  const byLesson = new Map<string, { present: number; total: number; order: number }>();
  groups.forEach((group) => {
    group.lessons.forEach((lesson) => {
      group.enrollments.forEach((enrollment) => {
        const value = enrollment.attendance?.[lesson.lessonNumber];
        if (!value) return;
        const bucket = byLesson.get(lesson.lessonNumber) || { present: 0, total: 0, order: lesson.order };
        bucket.total += 1;
        if (value === "present") bucket.present += 1;
        byLesson.set(lesson.lessonNumber, bucket);
      });
    });
  });
  return Array.from(byLesson.entries())
    .sort((left, right) => left[1].order - right[1].order)
    .map(([name, bucket]) => ({ name, rate: Math.round((bucket.present / bucket.total) * 100) }));
}

function homeworkByGroupRows(groups: GroupGradebook[]) {
  return groups
    .map((group) => {
      const students = group.enrollments.length;
      const lessons = group.lessons.length;
      if (!students || !lessons) return null;
      let checked = 0;
      group.enrollments.forEach((enrollment) => {
        group.lessons.forEach((lesson) => {
          if (enrollment.homework?.[lesson.lessonNumber] != null) checked += 1;
        });
      });
      return { name: group.group.name, rate: Math.round((checked / (students * lessons)) * 100) };
    })
    .filter((row): row is { name: string; rate: number } => row !== null && row.rate > 0);
}

function aapTrendRows(groups: GroupGradebook[]) {
  const byLesson = new Map<string, { sum: number; count: number; order: number }>();
  groups.forEach((group) => {
    group.lessons.forEach((lesson) => {
      group.enrollments.forEach((enrollment) => {
        const value = Number(enrollment.homework?.[lesson.lessonNumber]);
        if (!Number.isFinite(value) || value <= 0) return;
        const bucket = byLesson.get(lesson.lessonNumber) || { sum: 0, count: 0, order: lesson.order };
        bucket.sum += value;
        bucket.count += 1;
        byLesson.set(lesson.lessonNumber, bucket);
      });
    });
  });
  return Array.from(byLesson.entries())
    .sort((left, right) => left[1].order - right[1].order)
    .map(([name, bucket]) => ({ name, score: Number((bucket.sum / bucket.count).toFixed(1)) }));
}

function groupComparisonRows(groups: GroupGradebook[]) {
  return groups
    .map((group) => {
      const grades = group.enrollments.map((enrollment) => enrollment.averageGrade).filter((value) => value > 0);
      if (!grades.length) return null;
      return {
        name: group.group.name,
        avg: Number((grades.reduce((sum, value) => sum + value, 0) / grades.length).toFixed(1)),
      };
    })
    .filter((row): row is { name: string; avg: number } => row !== null);
}

function ChartShell({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <section className="rounded-[1rem] border border-[#E4E7EC] bg-white p-4 shadow-sm">
      <p className="text-sm font-black text-[#12203D]">{title}</p>
      <p className="mt-0.5 text-[11.5px] font-semibold text-[#7A8296]">{subtitle}</p>
      <div className="mt-3 h-44">{children}</div>
    </section>
  );
}

export default function ActiveTeacherCharts({ groups }: { groups: GroupGradebook[] }) {
  const attendanceRows = useMemo(() => attendanceTrendRows(groups), [groups]);
  const aapRows = useMemo(() => aapTrendRows(groups), [groups]);
  const homeworkRows = useMemo(() => homeworkByGroupRows(groups), [groups]);
  const comparisonRows = useMemo(() => groupComparisonRows(groups), [groups]);

  const cards = [
    attendanceRows.length > 1 ? (
      <ChartShell key="attendance" title="Attendance trend" subtitle="Present rate by lesson">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={attendanceRows} margin={{ top: 10, right: 8, left: -18, bottom: 0 }}>
            <defs>
              <linearGradient id="teacherAttendance" x1="0" x2="0" y1="0" y2="1">
                <stop offset="5%" stopColor="#2F5DE0" stopOpacity={0.28} />
                <stop offset="95%" stopColor="#2F5DE0" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#EEF1F6" strokeDasharray="4 4" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#7A8296" }} axisLine={false} tickLine={false} />
            <YAxis domain={[0, 100]} hide />
            <Tooltip formatter={(value: number) => [`${value}%`, "Attendance"]} />
            <Area dataKey="rate" type="monotone" stroke="#2F5DE0" strokeWidth={2.5} fill="url(#teacherAttendance)" />
          </AreaChart>
        </ResponsiveContainer>
      </ChartShell>
    ) : null,
    aapRows.length > 1 ? (
      <ChartShell key="aap" title="AAP trend" subtitle="Average homework performance by lesson">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={aapRows} margin={{ top: 10, right: 8, left: -18, bottom: 0 }}>
            <defs>
              <linearGradient id="teacherAap" x1="0" x2="0" y1="0" y2="1">
                <stop offset="5%" stopColor="#12203D" stopOpacity={0.22} />
                <stop offset="95%" stopColor="#12203D" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#EEF1F6" strokeDasharray="4 4" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#7A8296" }} axisLine={false} tickLine={false} />
            <YAxis domain={[0, 10]} hide />
            <Tooltip formatter={(value: number) => [value.toFixed(1), "AAP"]} />
            <Area dataKey="score" type="monotone" stroke="#12203D" strokeWidth={2.5} fill="url(#teacherAap)" />
          </AreaChart>
        </ResponsiveContainer>
      </ChartShell>
    ) : null,
    homeworkRows.length ? (
      <ChartShell key="homework" title="Homework submission" subtitle="Checked homework share by group">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={homeworkRows} margin={{ top: 10, right: 8, left: -18, bottom: 0 }}>
            <CartesianGrid stroke="#EEF1F6" strokeDasharray="4 4" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#7A8296" }} axisLine={false} tickLine={false} />
            <YAxis domain={[0, 100]} hide />
            <Tooltip formatter={(value: number) => [`${value}%`, "Homework"]} />
            <Bar dataKey="rate" fill="#2F5DE0" radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartShell>
    ) : null,
    comparisonRows.length > 1 ? (
      <ChartShell key="comparison" title="Group comparison" subtitle="Average academic performance by group">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={comparisonRows} margin={{ top: 10, right: 8, left: -18, bottom: 0 }}>
            <CartesianGrid stroke="#EEF1F6" strokeDasharray="4 4" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#7A8296" }} axisLine={false} tickLine={false} />
            <YAxis hide />
            <Tooltip />
            <Bar dataKey="avg" fill="#12203D" radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartShell>
    ) : null,
  ].filter(Boolean);

  if (!cards.length) return null;

  return <div className="grid gap-3 lg:grid-cols-2">{cards}</div>;
}
