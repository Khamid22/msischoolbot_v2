import { useState } from "react";
import { BarChart3, Calculator, Trophy } from "lucide-react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { TelegramLayout, Topbar } from "@/shared/ui/TelegramLayout";

interface ScopeOption {
  code: string;
  label: string;
  is_current?: boolean;
  url: string;
}

interface LeaderboardRow {
  rank: number;
  studentId: number;
  displayName: string;
  group: string;
  averageCompositeDisplay: string;
  examPerformance: number;
  examPerformanceDisplay?: string;
  examCount?: number;
  aap: number;
  aapDisplay?: string;
  homeworkCount?: number;
  attendanceRate: number;
  attendanceScoreDisplay?: string;
  attendanceTotal?: number;
  isProvisional?: boolean;
  ratingStatus?: string;
}

interface RatingPageProps {
  backUrl?: string;
  subjectName?: string;
  currentStudentId?: number;
  leaderboard?: LeaderboardRow[];
  scopeOptions?: ScopeOption[];
  ratingScopeLabel?: string;
}

export default function RatingPage(props: RatingPageProps) {
  const leaderboard = Array.isArray(props.leaderboard) ? props.leaderboard : [];
  const scopeOptions = Array.isArray(props.scopeOptions) ? props.scopeOptions : [];
  const [formulaOpen, setFormulaOpen] = useState(false);
  const subtitle = `Top performers in ${props.subjectName || "this subject"}${props.ratingScopeLabel ? ` · ${props.ratingScopeLabel}` : ""}`;
  const content = (
    <ChartCard
      title="Subject Ranking"
      subtitle={subtitle}
      icon={<BarChart3 className="h-4 w-4 text-info" />}
      headerActions={
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setFormulaOpen((current) => !current)}
            className={`inline-flex h-8 items-center gap-1.5 rounded-lg border px-3 text-[0.6875rem] font-bold transition-colors ${
              formulaOpen
                ? "border-foreground/20 bg-foreground text-background"
                : "border-foreground/10 bg-surface text-foreground hover:bg-muted"
            }`}
            aria-expanded={formulaOpen}
          >
            <Calculator className="h-3.5 w-3.5" />
            Formula
          </button>
          {scopeOptions.length ? (
            <div className="flex rounded-lg bg-muted p-0.5">
              {scopeOptions.map((option) => (
                <a
                  key={option.code}
                  href={option.url}
                  className={`rounded-md px-3 py-1.5 text-[0.6875rem] font-semibold transition-colors ${
                    option.is_current ? "bg-surface text-foreground shadow-sm" : "text-muted-foreground"
                  }`}
                >
                  {option.label}
                </a>
              ))}
            </div>
          ) : null}
        </div>
      }
    >
      {formulaOpen ? (
        <div className="mb-3 rounded-lg border border-foreground/10 bg-background px-3 py-3 text-xs leading-5 text-muted-foreground">
          <p className="font-bold text-foreground">Rating formula</p>
          <p className="mt-1">
            <span className="font-semibold text-foreground">AVG</span> = 70% EP + 15% AAP + 15% AR Score.
          </p>
          <p>
            EP uses the best attempt from each exam. AR Score is attendance percent converted to a 9-point score.
          </p>
          <p className="mt-1">
            Official ranking requires 2 exams, 10 homework grades, and 10 attendance sessions. Others are provisional.
          </p>
        </div>
      ) : null}
      {leaderboard.length ? (
        <>
        <div className="space-y-2 sm:hidden">
          {leaderboard.map((row, index) => (
            <div
              key={`${row.rank}-${row.studentId}-${row.group}-${row.displayName}-mobile`}
              className={`rounded-lg border p-3 ${
                row.studentId === props.currentStudentId
                  ? "border-info/30 bg-info/5"
                  : "border-foreground/8 bg-background"
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-[0.625rem] font-bold uppercase tracking-wide text-muted-foreground">
                    {row.isProvisional ? "Provisional" : `Rank #${row.rank || index + 1}`}
                  </p>
                  <p className="mt-0.5 break-words text-sm font-bold leading-snug">{row.displayName}</p>
                  <p className="mt-0.5 truncate text-xs text-muted-foreground">{row.group || "No group"}</p>
                </div>
                <div className="shrink-0 text-right">
                  <p className="font-display text-xl font-bold leading-none">{row.averageCompositeDisplay}</p>
                  <p className="mt-1 text-[0.625rem] font-bold uppercase tracking-wide text-muted-foreground">AVG</p>
                </div>
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                <div className="rounded-lg bg-muted px-2 py-2">
                  <p className="text-[0.625rem] font-bold uppercase text-muted-foreground">EP</p>
                  <p className="mt-0.5 text-xs font-bold">{row.examPerformanceDisplay || row.examPerformance}/9</p>
                </div>
                <div className="rounded-lg bg-muted px-2 py-2">
                  <p className="text-[0.625rem] font-bold uppercase text-muted-foreground">AAP</p>
                  <p className="mt-0.5 text-xs font-bold">{row.aapDisplay || row.aap}/9</p>
                </div>
                <div className="rounded-lg bg-muted px-2 py-2">
                  <p className="text-[0.625rem] font-bold uppercase text-muted-foreground">AR</p>
                  <p className="mt-0.5 text-xs font-bold">{row.attendanceRate}%</p>
                </div>
              </div>
              <div className="mt-3">
                <span
                  className={`inline-flex rounded-md px-2 py-1 text-[0.625rem] font-bold ${
                    row.isProvisional
                      ? "bg-warning/20 text-foreground"
                      : "bg-success/10 text-success"
                  }`}
                >
                  {row.isProvisional ? "Needs more data" : "Official ranking"}
                </span>
              </div>
            </div>
          ))}
        </div>

        <div className="miniapp-table-scroll hidden max-h-[70dvh] sm:block">
          <table className="w-full min-w-[51.25rem] text-left">
            <thead className="sticky top-0 z-20 bg-surface shadow-[0_0.0625rem_0_hsl(var(--foreground)/0.08)]">
              <tr className="border-b border-foreground/5">
                {["#", "Student", "Grp", "Status", "AVG", "EP", "AAP", "AR%"].map((heading) => (
                  <th
                    key={heading}
                    className="bg-surface px-3 py-2 text-[0.625rem] font-bold uppercase tracking-wider text-muted-foreground"
                  >
                    {heading}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {leaderboard.map((row, index) => (
                <tr
                  key={`${row.rank}-${row.studentId}-${row.group}-${row.displayName}`}
                  className={`border-b border-foreground/5 last:border-b-0 ${row.studentId === props.currentStudentId ? "bg-info/5" : "hover:bg-muted/40"}`}
                >
                  <td className="w-10 px-3 py-3 text-xs font-bold">{row.isProvisional ? "—" : row.rank || index + 1}</td>
                  <td className="px-3 py-3">
                    <span className="block text-xs font-medium leading-snug">{row.displayName}</span>
                  </td>
                  <td className="px-3 py-3">
                    <span className="block truncate text-xs text-muted-foreground">{row.group}</span>
                  </td>
                  <td className="px-3 py-3">
                    <span
                      className={`inline-flex rounded-md px-2 py-1 text-[0.625rem] font-bold ${
                        row.isProvisional
                          ? "bg-warning/20 text-foreground"
                          : "bg-success/10 text-success"
                      }`}
                      title={
                        row.isProvisional
                          ? `${row.examCount || 0}/2 exams, ${row.homeworkCount || 0}/10 homework, ${row.attendanceTotal || 0}/10 attendance`
                          : "Enough data for official ranking"
                      }
                    >
                      {row.isProvisional ? "Provisional" : "Official"}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-xs font-bold">{row.averageCompositeDisplay}</td>
                  <td className="px-3 py-3 text-xs">{row.examPerformanceDisplay || row.examPerformance}/9</td>
                  <td className="px-3 py-3 text-xs">{row.aapDisplay || row.aap}/9</td>
                  <td className="px-3 py-3 text-xs">{row.attendanceRate}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        </>
      ) : (
        <p className="text-sm text-muted-foreground">No rating data available.</p>
      )}
    </ChartCard>
  );

  return (
    <TelegramLayout
      topbar={
        <Topbar
          backUrl={props.backUrl}
          title="Rating Board"
          titleIcon={<Trophy className="h-5 w-5 text-trophy" />}
        />
      }
    >
      <div className="animate-in">{content}</div>
    </TelegramLayout>
  );
}
