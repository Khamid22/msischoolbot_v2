import { useQuery } from "@tanstack/react-query";
import { GraduationCap, Search, UserCheck } from "lucide-react";
import { useMemo, useState } from "react";

import { recruitmentRequest } from "@/features/recruitment/api";
import { dateTimeLabel, type RecruitmentCandidate } from "@/features/recruitment/model";
import { RECRUITMENT_API, fieldClass, queryError } from "@/features/recruitment/ui";

type CandidatePage = { items: RecruitmentCandidate[]; total: number };

export function TeachersView({ basePath }: { basePath: string }) {
  const [stage, setStage] = useState<"teacher_academy" | "active_teacher">("teacher_academy");
  const [search, setSearch] = useState("");
  const academy = useQuery({
    queryKey: ["recruitment", "teachers", "teacher_academy", search],
    queryFn: () => recruitmentRequest<CandidatePage>(`${RECRUITMENT_API}/candidates?stage=teacher_academy&per_page=100&search=${encodeURIComponent(search)}`),
  });
  const active = useQuery({
    queryKey: ["recruitment", "teachers", "active_teacher", search],
    queryFn: () => recruitmentRequest<CandidatePage>(`${RECRUITMENT_API}/candidates?stage=active_teacher&per_page=100&search=${encodeURIComponent(search)}`),
  });
  const selected = stage === "teacher_academy" ? academy : active;
  const items = useMemo(() => selected.data?.items || [], [selected.data]);

  return (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-[1fr_1fr_minmax(14rem,2fr)]">
        <button type="button" onClick={() => setStage("teacher_academy")} className={`flex min-h-20 items-center justify-between rounded-xl border p-3 text-left transition-[border-color,background-color,transform] duration-150 motion-reduce:transition-none ${stage === "teacher_academy" ? "border-amber-500 bg-amber-500/10" : "border-border bg-card hover:bg-muted/50"}`}>
          <span className="flex items-center gap-3"><GraduationCap className="h-5 w-5 text-amber-600" /><span><strong className="block text-sm">Teacher Academy</strong><span className="text-xs text-muted-foreground">Approved Academy intake</span></span></span>
          <span className="text-xl font-bold tabular-nums">{academy.data?.total || 0}</span>
        </button>
        <button type="button" onClick={() => setStage("active_teacher")} className={`flex min-h-20 items-center justify-between rounded-xl border p-3 text-left transition-[border-color,background-color,transform] duration-150 motion-reduce:transition-none ${stage === "active_teacher" ? "border-emerald-700 bg-emerald-700/10" : "border-border bg-card hover:bg-muted/50"}`}>
          <span className="flex items-center gap-3"><UserCheck className="h-5 w-5 text-emerald-700" /><span><strong className="block text-sm">Active Teachers</strong><span className="text-xs text-muted-foreground">Approved active intake</span></span></span>
          <span className="text-xl font-bold tabular-nums">{active.data?.total || 0}</span>
        </button>
        <label className="relative self-stretch"><span className="sr-only">Search teachers</span><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><input value={search} onChange={(event) => setSearch(event.target.value)} className={`${fieldClass} h-full min-h-11 pl-9`} placeholder="Search teachers" /></label>
      </div>
      {selected.isLoading ? <div className="rounded-xl border border-border bg-card p-6 text-sm text-muted-foreground">Loading teachers…</div> : null}
      {selected.error ? <div role="alert" className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">{queryError(selected.error)}</div> : null}
      {!selected.isLoading && !selected.error ? (
        <section className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((candidate) => <a key={candidate.id} href={`${basePath}/candidates/${candidate.id}?origin=teachers`} className="rounded-xl border border-border bg-card p-4 transition-[transform,box-shadow,border-color] duration-150 hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-card-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 motion-reduce:transform-none motion-reduce:transition-none"><strong className="block truncate text-sm">{candidate.full_name}</strong><span className="mt-1 block truncate text-xs text-muted-foreground">{candidate.applied_position || candidate.subject || "Position not set"}</span><span className="mt-3 block text-[11px] font-medium text-muted-foreground">Finalized {dateTimeLabel(candidate.final_decision_at)}</span></a>)}
          {!items.length ? <div className="col-span-full rounded-xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">No recruitment-linked teachers in this view.</div> : null}
        </section>
      ) : null}
    </div>
  );
}
