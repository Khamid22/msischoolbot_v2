import { Activity, BarChart3, Calendar } from "lucide-react";
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

interface AttendanceDatum {
  name: string;
  value: number;
}

interface DashboardChartsSectionProps {
  attendanceTotal: number;
  attendanceRate: number;
  presentCount: number;
  absentCount: number;
  justifiedCount: number;
  attendanceData: AttendanceDatum[];
  examChartData: Array<Record<string, string | number | null>>;
  examAttempts: string[];
  homeworkChartData: Array<Record<string, string | number | null>>;
}

const attendanceColors = ["#111111", "#888888", "#cccccc"];
const examSeriesColors = ["#111111", "#444444", "#777777", "#aaaaaa", "#dddddd"];

export default function DashboardChartsSection(props: DashboardChartsSectionProps) {
  const {
    attendanceTotal,
    attendanceRate,
    presentCount,
    absentCount,
    justifiedCount,
    attendanceData,
    examChartData,
    examAttempts,
    homeworkChartData,
  } = props;

  return (
    <>
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
                    <strong className="block font-display text-2xl leading-none">{attendanceRate || 0}%</strong>
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
                <Area type="monotone" dataKey="score" stroke="#111111" fill="#aaaaaa" fillOpacity={0.35} strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No homework grades yet.</p>
        )}
      </ChartCard>
    </>
  );
}
