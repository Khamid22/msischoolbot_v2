import { BarChart3, Trophy } from "lucide-react";
import { ChartCard } from "@/components/ChartCard";
import { TelegramLayout, Topbar } from "@/components/TelegramLayout";

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
  aap: number;
  attendanceRate: number;
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
      <div className="animate-in">
        <ChartCard
          title="Subject Ranking"
          subtitle={`Top performers in ${props.subjectName || "this subject"}${props.ratingScopeLabel ? ` · ${props.ratingScopeLabel}` : ""}`}
          icon={<BarChart3 className="h-4 w-4 text-info" />}
          headerActions={
            scopeOptions.length ? (
              <div className="flex rounded-lg bg-muted p-0.5">
                {scopeOptions.map((option) => (
                  <a
                    key={option.code}
                    href={option.url}
                    className={`rounded-md px-3 py-1.5 text-[11px] font-semibold transition-colors ${
                      option.is_current ? "bg-surface text-foreground shadow-sm" : "text-muted-foreground"
                    }`}
                  >
                    {option.label}
                  </a>
                ))}
              </div>
            ) : null
          }
        >
          {leaderboard.length ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left">
                <thead>
                  <tr className="border-b border-foreground/5">
                    {["#", "Student", "Group", "AVG", "EP", "AAP", "AR"].map((heading) => (
                      <th
                        key={heading}
                        className="sticky top-[calc(5rem+var(--tg-safe-offset))] z-10 bg-surface px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground sm:top-[calc(5.25rem+var(--tg-safe-offset))]"
                      >
                        {heading}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {leaderboard.map((row) => (
                    <tr
                      key={row.studentId}
                      className={`border-b border-foreground/5 ${row.studentId === props.currentStudentId ? "bg-info/5" : "hover:bg-muted/40"}`}
                    >
                      <td className="px-3 py-2.5 text-xs font-bold">{row.rank}</td>
                      <td className="max-w-[200px] px-3 py-2.5 text-xs font-medium leading-snug sm:text-sm">
                        <span className="inline-block whitespace-normal break-words">{row.displayName}</span>
                      </td>
                      <td className="px-3 py-2.5 text-xs text-muted-foreground">{row.group}</td>
                      <td className="px-3 py-2.5 text-xs font-bold">{row.averageCompositeDisplay}</td>
                      <td className="px-3 py-2.5 text-xs">{row.examPerformance}/9</td>
                      <td className="px-3 py-2.5 text-xs">{row.aap}/9</td>
                      <td className="px-3 py-2.5 text-xs">{row.attendanceRate}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No rating data available.</p>
          )}
        </ChartCard>
      </div>
    </TelegramLayout>
  );
}
