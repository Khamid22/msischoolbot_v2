import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Download, Plus, Save } from "lucide-react";
import { groups, subjects, gradebookColumns, getInitialGradebook, type AttendanceMark } from "@/lib/academic-data";
import { students } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_app/groups/$groupId")({
  component: GradebookPage,
  loader: ({ params }) => {
    const group = groups.find((g) => g.id === params.groupId);
    if (!group) throw notFound();
    return { group };
  },
  notFoundComponent: () => (
    <div className="p-10 text-center">
      <p className="text-sm text-muted-foreground">Group not found.</p>
      <Button asChild variant="link"><Link to="/groups">Back to groups</Link></Button>
    </div>
  ),
  errorComponent: ({ error }) => (
    <div className="p-10 text-center text-sm text-destructive">{error.message}</div>
  ),
  head: ({ params }) => ({ meta: [{ title: `Gradebook — ${params.groupId}` }] }),
});

const ATT_OPTIONS: AttendanceMark[] = ["P", "A", "L", ""];

function GradebookPage() {
  const { group } = Route.useLoaderData();
  const subject = subjects.find((s) => s.id === group.subjectId);
  const [cells, setCells] = useState(() => getInitialGradebook(group.id));

  const rows = useMemo(
    () => group.studentIds.map((id: string) => students.find((s) => s.id === id)).filter(Boolean) as typeof students,
    [group.studentIds],
  );

  function update(studentId: string, colId: string, value: string) {
    setCells((prev) => ({ ...prev, [studentId]: { ...prev[studentId], [colId]: value } }));
  }

  function attendanceColor(v: string) {
    if (v === "P") return "bg-success/15 text-success";
    if (v === "A") return "bg-destructive/15 text-destructive";
    if (v === "L") return "bg-warning/20 text-warning-foreground";
    return "text-muted-foreground";
  }

  function rowAverage(studentId: string) {
    let total = 0, weight = 0;
    for (const c of gradebookColumns) {
      if (c.kind !== "score") continue;
      const raw = cells[studentId]?.[c.id];
      const n = Number(raw);
      if (Number.isFinite(n)) {
        total += (n / c.max) * c.weight;
        weight += c.weight;
      }
    }
    return weight === 0 ? "—" : ((total / weight) * 100).toFixed(1);
  }

  function rowAttendance(studentId: string) {
    const att = gradebookColumns.filter((c) => c.kind === "attendance");
    const present = att.filter((c) => cells[studentId]?.[c.id] === "P").length;
    return Math.round((present / att.length) * 100);
  }

  return (
    <>
      <PageHeader
        title={group.name}
        description={`${subject?.name ?? ""} · ${group.yearLevel} · ${rows.length} students`}
        actions={
          <>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/groups"><ArrowLeft className="h-4 w-4" /> All groups</Link>
            </Button>
            <Button variant="outline" size="sm"><Download className="h-4 w-4" /> Export CSV</Button>
            <Button variant="outline" size="sm"><Plus className="h-4 w-4" /> Add column</Button>
            <Button size="sm"><Save className="h-4 w-4" /> Save</Button>
          </>
        }
      />

      <div className="px-4 md:px-6 pb-8">
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full border-separate border-spacing-0 text-sm">
              <thead>
                <tr>
                  <th className="sticky left-0 z-20 min-w-[220px] border-b border-r border-border bg-muted/60 px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Student
                  </th>
                  {gradebookColumns.map((c) => (
                    <th
                      key={c.id}
                      className={cn(
                        "border-b border-border px-2 py-2.5 text-center text-xs font-semibold",
                        c.kind === "attendance" ? "min-w-[64px] bg-accent/40 text-accent-foreground" : "min-w-[80px] bg-muted/60 text-muted-foreground",
                      )}
                    >
                      <div className="leading-tight">{c.label}</div>
                      <div className="mt-0.5 text-[10px] font-normal opacity-70">
                        {c.kind === "attendance" ? "Attendance" : `/${c.max} · ${c.weight}%`}
                      </div>
                    </th>
                  ))}
                  <th className="border-b border-l border-border bg-primary-soft px-3 py-2.5 text-center text-xs font-semibold uppercase tracking-wide text-primary">
                    Grade
                  </th>
                  <th className="border-b border-border bg-primary-soft px-3 py-2.5 text-center text-xs font-semibold uppercase tracking-wide text-primary">
                    Att %
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((s, i) => (
                  <tr key={s.id} className={i % 2 === 0 ? "bg-background" : "bg-muted/20"}>
                    <td className="sticky left-0 z-10 border-b border-r border-border bg-inherit px-3 py-2">
                      <div className="flex items-center gap-2.5">
                        <div
                          className="flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-semibold text-white"
                          style={{ background: s.avatarColor }}
                        >
                          {s.name.split(" ").map((w) => w[0]).slice(0, 2).join("")}
                        </div>
                        <div className="min-w-0">
                          <p className="truncate font-medium">{s.name}</p>
                          <p className="truncate text-[11px] text-muted-foreground">{s.id}</p>
                        </div>
                      </div>
                    </td>

                    {gradebookColumns.map((c) => {
                      const v = String(cells[s.id]?.[c.id] ?? "");
                      if (c.kind === "attendance") {
                        return (
                          <td key={c.id} className="border-b border-border p-0 text-center">
                            <select
                              value={v}
                              onChange={(e) => update(s.id, c.id, e.target.value)}
                              className={cn(
                                "h-9 w-full appearance-none bg-transparent text-center text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-ring",
                                attendanceColor(v),
                              )}
                            >
                              {ATT_OPTIONS.map((o) => (
                                <option key={o} value={o}>{o || "—"}</option>
                              ))}
                            </select>
                          </td>
                        );
                      }
                      return (
                        <td key={c.id} className="border-b border-border p-0 text-center">
                          <input
                            type="number"
                            min={0}
                            max={c.max}
                            value={v}
                            onChange={(e) => update(s.id, c.id, e.target.value)}
                            className="h-9 w-full bg-transparent text-center text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-ring"
                          />
                        </td>
                      );
                    })}

                    <td className="border-b border-l border-border bg-primary-soft/40 px-3 py-2 text-center font-semibold tabular-nums">
                      {rowAverage(s.id)}
                    </td>
                    <td className="border-b border-border bg-primary-soft/40 px-3 py-2 text-center tabular-nums">
                      <Badge
                        variant="secondary"
                        className={cn(
                          rowAttendance(s.id) >= 90 ? "bg-success/15 text-success" :
                          rowAttendance(s.id) >= 75 ? "bg-warning/20 text-warning-foreground" :
                          "bg-destructive/15 text-destructive",
                        )}
                      >
                        {rowAttendance(s.id)}%
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-success/40" /> P — Present</span>
          <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-destructive/40" /> A — Absent</span>
          <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-warning/40" /> L — Late</span>
          <span className="ml-auto">Click any cell to edit — changes are local until you press Save.</span>
        </div>
      </div>
    </>
  );
}
