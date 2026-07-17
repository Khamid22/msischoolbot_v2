import { useQuery } from "@tanstack/react-query";
import { GraduationCap, Search, UserCheck } from "lucide-react";
import { useMemo, useState, type KeyboardEvent } from "react";

import { recruitmentRequest } from "@/features/recruitment/api";
import { dateTimeLabel } from "@/features/recruitment/model";
import { RECRUITMENT_API, fieldClass, queryError } from "@/features/recruitment/ui";

type RecruitmentTeacher = {
  kind: "teacher_academy" | "active_teacher";
  record_id: number;
  recruitment_candidate_id: number;
  full_name: string;
  position: string;
  subject: string;
  status: string;
  onboarding_status: string;
  joined_at: string;
};

type TeacherPage = { items: RecruitmentTeacher[]; total: number };

function statusLabel(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function TeacherCard({ teacher, basePath }: { teacher: RecruitmentTeacher; basePath: string }) {
  const content = (
    <>
      <span className="flex items-start justify-between gap-2">
        <strong className="block min-w-0 truncate text-sm">{teacher.full_name}</strong>
        {teacher.onboarding_status === "pending" ? <span className="shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-800">Onboarding pending</span> : null}
      </span>
      <span className="mt-1 block truncate text-xs text-muted-foreground">{teacher.position || teacher.subject || "Position not set"}</span>
      <span className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] font-medium text-muted-foreground">
        <span>{teacher.kind === "teacher_academy" ? "Academy since" : "Active since"} {dateTimeLabel(teacher.joined_at)}</span>
        {teacher.status ? <span aria-label={`Status: ${statusLabel(teacher.status)}`}>· {statusLabel(teacher.status)}</span> : null}
      </span>
    </>
  );
  const classes = "rounded-xl border border-border bg-card p-4 transition-[transform,box-shadow,border-color] duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 motion-reduce:transform-none motion-reduce:transition-none";
  if (teacher.recruitment_candidate_id) {
    return <a href={`${basePath}/candidates/${teacher.recruitment_candidate_id}?origin=teachers`} className={`${classes} hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-card-hover`}>{content}</a>;
  }
  return <article className={classes}>{content}</article>;
}

export function TeachersView({ basePath }: { basePath: string }) {
  const [stage, setStage] = useState<"teacher_academy" | "active_teacher">("teacher_academy");
  const [search, setSearch] = useState("");
  const academy = useQuery({
    queryKey: ["recruitment", "teachers", "teacher_academy", search],
    queryFn: () => recruitmentRequest<TeacherPage>(`${RECRUITMENT_API}/teachers?kind=teacher_academy&per_page=100&search=${encodeURIComponent(search)}`),
  });
  const active = useQuery({
    queryKey: ["recruitment", "teachers", "active_teacher", search],
    queryFn: () => recruitmentRequest<TeacherPage>(`${RECRUITMENT_API}/teachers?kind=active_teacher&per_page=100&search=${encodeURIComponent(search)}`),
  });
  const selected = stage === "teacher_academy" ? academy : active;
  const items = useMemo(() => selected.data?.items || [], [selected.data]);
  const selectTabFromKeyboard = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === "ArrowLeft" || event.key === "Home" ? "teacher_academy" : "active_teacher";
    setStage(next);
    requestAnimationFrame(() => document.getElementById(`teachers-tab-${next}`)?.focus());
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
        <div role="tablist" aria-label="Teacher status" className={`no-scrollbar flex min-w-0 flex-1 items-end overflow-x-auto border-b-2 ${stage === "teacher_academy" ? "border-amber-500" : "border-emerald-700"}`}>
          <button id="teachers-tab-teacher_academy" type="button" role="tab" aria-selected={stage === "teacher_academy"} aria-controls="teachers-panel" tabIndex={stage === "teacher_academy" ? 0 : -1} onKeyDown={selectTabFromKeyboard} onClick={() => setStage("teacher_academy")} className={`relative flex min-h-12 min-w-[12rem] items-center gap-2 px-4 pr-8 text-left text-sm font-semibold [clip-path:polygon(0_0,calc(100%-1.25rem)_0,100%_100%,0_100%)] transition-[background-color,color,transform] duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-3px] focus-visible:outline-primary motion-reduce:transition-none ${stage === "teacher_academy" ? "z-20 bg-amber-500 text-amber-950" : "z-10 bg-muted text-muted-foreground hover:bg-amber-100 hover:text-foreground"}`}>
            <GraduationCap className="h-4 w-4 shrink-0" />
            <span className="whitespace-nowrap">Teacher Academy</span>
            <span className={`ml-auto rounded-full px-2 py-0.5 text-xs tabular-nums ${stage === "teacher_academy" ? "bg-white/55" : "bg-card"}`}>{academy.data?.total || 0}</span>
          </button>
          <button id="teachers-tab-active_teacher" type="button" role="tab" aria-selected={stage === "active_teacher"} aria-controls="teachers-panel" tabIndex={stage === "active_teacher" ? 0 : -1} onKeyDown={selectTabFromKeyboard} onClick={() => setStage("active_teacher")} className={`relative -ml-4 flex min-h-12 min-w-[12rem] items-center gap-2 pl-8 pr-8 text-left text-sm font-semibold [clip-path:polygon(0_0,calc(100%-1.25rem)_0,100%_100%,0_100%)] transition-[background-color,color,transform] duration-150 focus-visible:z-30 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-3px] focus-visible:outline-primary motion-reduce:transition-none ${stage === "active_teacher" ? "z-20 bg-emerald-700 text-white" : "z-10 bg-muted text-muted-foreground hover:bg-emerald-100 hover:text-foreground"}`}>
            <UserCheck className="h-4 w-4 shrink-0" />
            <span className="whitespace-nowrap">Active Teachers</span>
            <span className={`ml-auto rounded-full px-2 py-0.5 text-xs tabular-nums ${stage === "active_teacher" ? "bg-white/20" : "bg-card"}`}>{active.data?.total || 0}</span>
          </button>
        </div>
        <label className="relative w-full shrink-0 sm:w-72"><span className="sr-only">Search teachers</span><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><input value={search} onChange={(event) => setSearch(event.target.value)} className={`${fieldClass} min-h-12 pl-9`} placeholder="Search teachers" /></label>
      </div>
      <div id="teachers-panel" role="tabpanel" aria-labelledby={`teachers-tab-${stage}`}>
        {selected.isLoading ? <div className="rounded-xl border border-border bg-card p-6 text-sm text-muted-foreground">Loading teachers…</div> : null}
        {selected.error ? <div role="alert" className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">{queryError(selected.error)}</div> : null}
        {!selected.isLoading && !selected.error ? (
          <section className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {items.map((teacher) => <TeacherCard key={`${teacher.kind}:${teacher.record_id}`} teacher={teacher} basePath={basePath} />)}
            {!items.length ? <div className="col-span-full rounded-xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">No teachers in this view.</div> : null}
          </section>
        ) : null}
      </div>
    </div>
  );
}
