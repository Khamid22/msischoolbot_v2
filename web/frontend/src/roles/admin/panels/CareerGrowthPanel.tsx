import { Award, BarChart3, GraduationCap, Layers, TrendingUp } from "lucide-react";
import type { ReactNode } from "react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { asNumber, asString } from "../shared";

const rankLabels: Record<string, string> = {
  junior: "Junior Teacher",
  trained: "Trained Teacher",
  experienced_igcse: "Experienced IGCSE Teacher",
};

const rankOrder = ["junior", "trained", "experienced_igcse"];

function normalizedRank(value: unknown) {
  const key = asString(value).toLowerCase();
  return rankLabels[key] ? key : "junior";
}

function rankLabel(value: unknown) {
  return rankLabels[normalizedRank(value)];
}

function nextRankLabel(value: unknown) {
  const index = rankOrder.indexOf(normalizedRank(value));
  const next = rankOrder[Math.min(rankOrder.length - 1, index + 1)];
  return next === normalizedRank(value) ? "Top rank reached" : rankLabels[next];
}

function progressPercent(value: unknown, target = 120) {
  return Math.max(0, Math.min(100, Math.round((asNumber(value) / target) * 100)));
}

function average(values: number[]) {
  if (!values.length) return 0;
  return Math.round((values.reduce((sum, value) => sum + value, 0) / values.length) * 10) / 10;
}

function teacherRows(state: any) {
  return Array.isArray(state.teachers)
    ? (state.teachers as Array<Record<string, unknown>>)
    : Array.isArray(state.props?.adminTeachers)
      ? (state.props.adminTeachers as Array<Record<string, unknown>>)
      : [];
}

function currentTeacherRows(state: any) {
  const rows = teacherRows(state);
  const login = asString(state.props?.authLogin).toLowerCase();
  const matched = rows.filter((row) => asString(row.full_name).toLowerCase() === login);
  return matched.length ? matched : rows;
}

function Metric({
  label,
  value,
  detail,
  icon,
  tone = "bg-background",
}: {
  label: string;
  value: string | number;
  detail: string;
  icon: ReactNode;
  tone?: string;
}) {
  return (
    <div className={`rounded-lg border border-foreground/10 p-3 ${tone}`}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">{label}</p>
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-surface text-foreground">
          {icon}
        </span>
      </div>
      <p className="mt-2 text-2xl font-bold leading-none">{value}</p>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">{detail}</p>
    </div>
  );
}

function ProgressLine({ value }: { value: number }) {
  return (
    <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted">
      <div className="h-full rounded-full bg-primary" style={{ width: `${value}%` }} />
    </div>
  );
}

export default function CareerGrowthPanel({ state }: { state: any }) {
  const rows = currentTeacherRows(state);
  const primary = rows[0];
  const assignedGroups = rows
    .map((row) => asString(row.assigned_group))
    .filter(Boolean);
  const supervisedLessons = rows.reduce((sum, row) => sum + asNumber(row.supervised_lessons), 0);
  const performanceScore = average(rows.map((row) => asNumber(row.performance_score)).filter((value) => value > 0));
  const rank = rankLabel(primary?.category);
  const nextRank = nextRankLabel(primary?.category);
  const rankProgress = progressPercent(supervisedLessons);
  const semesterStage = asString(primary?.semester_stage) || "1-2";
  const promotionNotes = rows.map((row) => asString(row.promotion_notes)).find(Boolean);
  const evidence = rows.map((row) => asString(row.igcse_evidence)).find(Boolean);

  if (!rows.length) {
    return (
      <ChartCard
        title="Career Growth"
        subtitle="Rank and teaching progress"
        icon={<TrendingUp className="h-4 w-4 text-info" />}
      >
        <div className="rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-10 text-center">
          <p className="text-sm font-bold">No teacher growth record is attached yet.</p>
          <p className="mt-1 text-xs text-muted-foreground">Admin can attach a teacher record to start rank tracking.</p>
        </div>
      </ChartCard>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric
          label="Current Rank"
          value={rank}
          detail={`Semester stage ${semesterStage}`}
          icon={<Award className="h-4 w-4" />}
          tone="bg-emerald-50"
        />
        <Metric
          label="Next Rank"
          value={nextRank}
          detail={`${rankProgress}% progress`}
          icon={<TrendingUp className="h-4 w-4" />}
          tone="bg-sky-50"
        />
        <Metric
          label="Lessons Conducted"
          value={supervisedLessons}
          detail="Recorded supervised lessons"
          icon={<GraduationCap className="h-4 w-4" />}
          tone="bg-amber-50"
        />
        <Metric
          label="Performance"
          value={performanceScore ? `${performanceScore}/10` : "-"}
          detail="Current evaluation score"
          icon={<BarChart3 className="h-4 w-4" />}
          tone="bg-violet-50"
        />
      </div>

      <ChartCard title="Rank Up Progress" subtitle="Growth requirements" icon={<TrendingUp className="h-4 w-4 text-info" />}>
        <div className="grid gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(18rem,0.6fr)]">
          <div className="rounded-lg border border-foreground/10 bg-background p-4">
            <div className="flex items-center justify-between gap-3 text-sm font-bold">
              <span>{rank}</span>
              <span>{supervisedLessons}/120 lessons</span>
            </div>
            <ProgressLine value={rankProgress} />
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              Rank-up progress is based on supervised lessons and performance review. Admin can update the score and promotion notes from the teacher records.
            </p>
          </div>

          <div className="rounded-lg border border-foreground/10 bg-background p-4">
            <div className="mb-3 flex items-center gap-2">
              <Layers className="h-4 w-4 text-info" />
              <p className="text-sm font-bold">Assigned Groups</p>
            </div>
            {assignedGroups.length ? (
              <div className="flex flex-wrap gap-2">
                {assignedGroups.map((group) => (
                  <span key={group} className="rounded-md bg-muted px-2 py-1 text-xs font-bold text-muted-foreground">
                    {group}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No groups attached yet.</p>
            )}
          </div>
        </div>
      </ChartCard>

      {promotionNotes || evidence ? (
        <ChartCard title="Growth Notes" subtitle="Admin guidance" icon={<Award className="h-4 w-4 text-info" />}>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-lg border border-foreground/10 bg-background p-4">
              <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Promotion Notes</p>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-foreground/80">
                {promotionNotes || "No promotion notes yet."}
              </p>
            </div>
            <div className="rounded-lg border border-foreground/10 bg-background p-4">
              <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">IGCSE Evidence</p>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-foreground/80">
                {evidence || "No evidence recorded yet."}
              </p>
            </div>
          </div>
        </ChartCard>
      ) : null}
    </div>
  );
}
