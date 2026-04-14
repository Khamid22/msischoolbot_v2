import { Search, Users } from "lucide-react";
import { ChartCard } from "@/components/ChartCard";
import { routes } from "@/lib/routes";
import { adminStickyTop, asNumber, asString, formatLastSeen } from "../shared";

export default function StudentsPanel({ state }: { state: any }) {
  const {
    searchQuery,
    setSearchQuery,
    currentSchool,
    schoolOptions,
    filteredStudents,
  } = state;

  return (
    <div className="space-y-4">
      <div
        className="sticky z-30 -mx-3 bg-background/95 px-3 pb-3 pt-1 backdrop-blur sm:-mx-4 sm:px-4 md:-mx-6 md:px-6"
        style={{ top: adminStickyTop }}
      >
        <div className="flex flex-col gap-3 sm:flex-row">
          <label className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Name, student ID, subject, or school"
              className="w-full rounded-xl border-2 border-foreground/10 bg-surface py-2.5 pl-10 pr-4 text-sm outline-none"
            />
          </label>
          <form action="/" method="get" className="shrink-0">
            <input type="hidden" name="panel" value="students" />
            <select
              name="school"
              defaultValue={currentSchool}
              onChange={(event) => event.currentTarget.form?.submit()}
              className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm font-medium outline-none sm:w-52"
            >
              {schoolOptions.map((option: { code: string; label: string }) => (
                <option key={option.code} value={option.code}>
                  {option.label}
                </option>
              ))}
            </select>
          </form>
        </div>
      </div>

      <ChartCard
        title="Students"
        subtitle={`${filteredStudents.length} results`}
        icon={<Users className="h-4 w-4 text-info" />}
      >
        <div className="max-h-[68dvh] overflow-auto">
          <table className="w-full min-w-[720px] text-left">
            <thead>
              <tr className="sticky top-0 z-10 border-b border-foreground/5 bg-surface">
                {["ID", "Full Name", "Subjects", "School", "Last Seen"].map((heading) => (
                  <th
                    key={heading}
                    className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground"
                  >
                    {heading}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredStudents.length ? (
                filteredStudents.map((student: Record<string, unknown>) => {
                  const seen = formatLastSeen(student.last_seen_at);
                  return (
                    <tr key={asNumber(student.id)} className="border-b border-foreground/5 hover:bg-muted/40">
                      <td className="px-3 py-2.5 text-xs font-bold">
                        <a
                          href={routes.adminStudentDashboard(asNumber(student.id), currentSchool)}
                          className="text-info hover:underline"
                        >
                          {asString(student.student_id)}
                        </a>
                      </td>
                      <td className="px-3 py-2.5 text-sm font-medium">
                        <a href={routes.adminStudentProfile(asNumber(student.id))} className="hover:underline">
                          {asString(student.full_name)}
                        </a>
                      </td>
                      <td className="px-3 py-2.5 text-xs text-muted-foreground">
                        {asString(student.subjects)}
                      </td>
                      <td className="px-3 py-2.5 text-xs text-muted-foreground">
                        {asString(student.school_name)}
                      </td>
                      <td className="px-3 py-2.5 text-xs">
                        <span className={seen.online ? "font-semibold text-green-500" : "text-muted-foreground"}>
                          {seen.label}
                        </span>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={5} className="px-3 py-4 text-sm text-muted-foreground">
                    No students match your search.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </ChartCard>
    </div>
  );
}
