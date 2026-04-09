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
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-foreground/5">
                  {["#", "Student", "Grp", "AVG", "EP", "AAP", "AR%"].map((heading) => (
                    <th
                      key={heading}
                      className="sticky top-0 z-10 bg-surface px-1.5 py-2 text-[9px] font-bold uppercase tracking-wider text-muted-foreground sm:px-3 sm:text-[10px]"
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
                    className={`border-b border-foreground/5 ${row.studentId === props.currentStudentId ? "bg-info/5" : "hover:bg-muted/40"}`}
                  >
                    <td className="w-6 px-1.5 py-2 text-[10px] font-bold sm:px-3 sm:text-xs">{index + 1}</td>
                    <td className="max-w-[90px] px-1.5 py-2 sm:max-w-[200px] sm:px-3">
                      <span className="block truncate text-[10px] font-medium sm:text-xs">{row.displayName}</span>
                    </td>
                    <td className="max-w-[52px] px-1.5 py-2 sm:px-3">
                      <span className="block truncate text-[10px] text-muted-foreground sm:text-xs">{row.group}</span>
                    </td>
                    <td className="px-1.5 py-2 text-[10px] font-bold sm:px-3 sm:text-xs">{row.averageCompositeDisplay}</td>
                    <td className="px-1.5 py-2 text-[10px] sm:px-3 sm:text-xs">{row.examPerformance}/9</td>
                    <td className="px-1.5 py-2 text-[10px] sm:px-3 sm:text-xs">{row.aap}/9</td>
                    <td className="px-1.5 py-2 text-[10px] sm:px-3 sm:text-xs">{row.attendanceRate}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-sm text-muted-foreground">No rating data available.</p>
          )}
        </ChartCard>
      </div>
    </TelegramLayout>
  );
}
