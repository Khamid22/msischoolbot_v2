import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ExternalLink, GraduationCap, Loader2, Search, UserCheck, UserMinus } from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent, type KeyboardEvent, type MouseEvent } from "react";

import { jsonBody, recruitmentRequest } from "@/features/recruitment/api";
import { dateLabel, type RecruitmentOptions } from "@/features/recruitment/model";
import {
  RECRUITMENT_API,
  buttonClass,
  fieldClass,
  queryError,
  replaceUrlParams,
  secondaryButtonClass,
} from "@/features/recruitment/ui";
import { ActionMenu, type ActionMenuItem } from "@/shared/ui/ActionMenu";
import type { FloatingToastTone } from "@/shared/ui/FloatingToast";
import { MobileCardList } from "@/shared/ui/MobileCardList";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";
import { ProgressBar } from "@/shared/ui/ProgressBar";
import { ResponsiveTable } from "@/shared/ui/ResponsiveTable";

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
  added_on: string;
  assigned_count: number;
  passed_count: number;
  average_score: number | null;
  can_remove: boolean;
  generated_login_will_be_deleted: boolean;
};

type TeacherPage = { items: RecruitmentTeacher[]; total: number };
type RemovalResult = {
  message: string;
  identity_deleted: boolean;
  already_removed: boolean;
};

function statusLabel(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (character: string) => character.toUpperCase());
}

function initialTeacherFilters() {
  if (typeof window === "undefined") {
    return { stage: "teacher_academy" as const, search: "", subjectId: "" };
  }
  const params = new URLSearchParams(window.location.search);
  return {
    stage: params.get("teacher_tab") === "active_teacher"
      ? "active_teacher" as const
      : "teacher_academy" as const,
    search: params.get("teacher_search") || "",
    subjectId: params.get("teacher_subject") || "",
  };
}

function profileHref(teacher: RecruitmentTeacher, basePath: string) {
  return teacher.recruitment_candidate_id
    ? `${basePath}/candidates/${teacher.recruitment_candidate_id}?origin=teachers`
    : "";
}

function isInteractiveTarget(target: EventTarget | null) {
  return target instanceof Element
    && Boolean(target.closest("a,button,input,select,textarea,[role='menuitem']"));
}

function openProfile(teacher: RecruitmentTeacher, basePath: string) {
  const href = profileHref(teacher, basePath);
  if (href) window.location.assign(href);
}

function teacherActions(
  teacher: RecruitmentTeacher,
  basePath: string,
  onRemove: (teacher: RecruitmentTeacher) => void,
): ActionMenuItem[] {
  const items: ActionMenuItem[] = [
    {
      key: "open",
      label: "Open profile",
      icon: <ExternalLink className="h-4 w-4" />,
      disabled: !teacher.recruitment_candidate_id,
      tooltip: teacher.recruitment_candidate_id ? undefined : "This teacher has no linked lifecycle profile.",
      onClick: () => openProfile(teacher, basePath),
    },
  ];
  if (teacher.can_remove) {
    items.push(
      { key: "remove-separator", separator: true },
      {
        key: "remove",
        label: "Remove from Teacher Academy",
        icon: <UserMinus className="h-4 w-4" />,
        danger: true,
        onClick: () => onRemove(teacher),
      },
    );
  }
  return items;
}

function AccountStatus({ teacher }: { teacher: RecruitmentTeacher }) {
  const pending = teacher.onboarding_status === "pending"
    || teacher.onboarding_status === "onboarding_pending"
    || teacher.onboarding_status === "missing_handoff";
  return (
    <span className={`inline-flex rounded-full px-2 py-1 text-[11px] font-semibold ${
      pending
        ? "bg-amber-100 text-amber-900"
        : "bg-emerald-100 text-emerald-900"
    }`}>
      {pending ? "Onboarding pending" : "Connected"}
    </span>
  );
}

function AcademyStatus({ status }: { status: string }) {
  const normalized = String(status || "").toLowerCase();
  const tone = normalized.includes("improvement")
    ? "bg-rose-100 text-rose-900"
    : normalized.includes("ready") || normalized.includes("passed")
      ? "bg-emerald-100 text-emerald-900"
      : "bg-sky-100 text-sky-900";
  return (
    <span className={`inline-flex rounded-full px-2 py-1 text-[11px] font-semibold ${tone}`}>
      {statusLabel(status || "in_training")}
    </span>
  );
}

function AcademyProgress({ teacher }: { teacher: RecruitmentTeacher }) {
  if (teacher.assigned_count <= 0) {
    return <span className="text-xs font-medium text-muted-foreground">Not started</span>;
  }
  return (
    <div className="w-44 max-w-full space-y-1.5">
      <ProgressBar
        value={teacher.passed_count}
        max={teacher.assigned_count}
        label={`${teacher.full_name}: ${teacher.passed_count} of ${teacher.assigned_count} Academy lessons passed`}
        fillClassName="bg-emerald-600"
      />
      <div className="flex justify-between gap-3 text-[11px] font-medium text-muted-foreground">
        <span>{teacher.passed_count}/{teacher.assigned_count} passed</span>
        <span>{teacher.average_score === null ? "No score" : `Avg ${teacher.average_score.toFixed(1)}`}</span>
      </div>
    </div>
  );
}

function TeacherMobileCard({
  teacher,
  basePath,
  onRemove,
}: {
  teacher: RecruitmentTeacher;
  basePath: string;
  onRemove: (teacher: RecruitmentTeacher) => void;
}) {
  const isAcademy = teacher.kind === "teacher_academy";
  return (
    <article className="rounded-xl border border-border bg-card p-3 shadow-sm">
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          {teacher.recruitment_candidate_id ? (
            <a
              href={profileHref(teacher, basePath)}
              className="block truncate text-sm font-semibold text-foreground hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
            >
              {teacher.full_name}
            </a>
          ) : (
            <strong className="block truncate text-sm">{teacher.full_name}</strong>
          )}
          <p className="mt-0.5 truncate text-xs text-muted-foreground">{teacher.position || "Position not set"}</p>
        </div>
        <ActionMenu
          label={`Actions for ${teacher.full_name}`}
          items={teacherActions(teacher, basePath, onRemove)}
        />
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 text-xs">
        <div>
          <dt className="font-medium text-muted-foreground">{isAcademy ? "Added to Academy" : "Active since"}</dt>
          <dd className="mt-0.5 font-semibold">{teacher.added_on ? dateLabel(teacher.added_on) : "Not recorded"}</dd>
        </div>
        <div>
          <dt className="font-medium text-muted-foreground">Subject</dt>
          <dd className="mt-0.5 font-semibold">{teacher.subject || "Not set"}</dd>
        </div>
        <div>
          <dt className="font-medium text-muted-foreground">{isAcademy ? "Academy status" : "Status"}</dt>
          <dd className="mt-1">{isAcademy ? <AcademyStatus status={teacher.status} /> : statusLabel(teacher.status)}</dd>
        </div>
        <div>
          <dt className="font-medium text-muted-foreground">Account</dt>
          <dd className="mt-1"><AccountStatus teacher={teacher} /></dd>
        </div>
      </dl>
      {isAcademy ? <div className="mt-3 border-t border-border pt-3"><AcademyProgress teacher={teacher} /></div> : null}
    </article>
  );
}

export function TeachersView({
  basePath,
  onAnnouncement,
}: {
  basePath: string;
  onAnnouncement: (message: string, tone?: FloatingToastTone) => void;
}) {
  const initialFilters = useMemo(initialTeacherFilters, []);
  const [stage, setStage] = useState<"teacher_academy" | "active_teacher">(initialFilters.stage);
  const [search, setSearch] = useState(initialFilters.search);
  const [subjectId, setSubjectId] = useState(initialFilters.subjectId);
  const [removeTeacher, setRemoveTeacher] = useState<RecruitmentTeacher | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const queryClient = useQueryClient();
  const options = useQuery({
    queryKey: ["recruitment", "options"],
    queryFn: () => recruitmentRequest<RecruitmentOptions>(`${RECRUITMENT_API}/options`),
  });
  const teacherQuery = (kind: RecruitmentTeacher["kind"]) => {
    const params = new URLSearchParams({
      kind,
      per_page: "100",
      search,
    });
    if (subjectId) params.set("subject_id", subjectId);
    return `${RECRUITMENT_API}/teachers?${params.toString()}`;
  };
  const academy = useQuery({
    queryKey: ["recruitment", "teachers", "teacher_academy", search, subjectId],
    queryFn: () => recruitmentRequest<TeacherPage>(teacherQuery("teacher_academy")),
  });
  const remove = useMutation({
    mutationFn: (values: { rejection_reason: string; reason_detail: string }) =>
      recruitmentRequest<RemovalResult>(
        `${RECRUITMENT_API}/teachers/${removeTeacher?.record_id}/remove`,
        { method: "POST", body: jsonBody(values) },
      ),
    onSuccess: (result) => {
      setRemoveTeacher(null);
      setRejectionReason("");
      onAnnouncement(result.message || "Teacher removed from Teacher Academy.");
      void queryClient.invalidateQueries({ queryKey: ["recruitment"] });
    },
    onError: (error) => onAnnouncement(queryError(error), "error"),
  });
  const active = useQuery({
    queryKey: ["recruitment", "teachers", "active_teacher", search, subjectId],
    queryFn: () => recruitmentRequest<TeacherPage>(teacherQuery("active_teacher")),
  });
  const selected = stage === "teacher_academy" ? academy : active;
  const items = useMemo(() => selected.data?.items || [], [selected.data]);
  useEffect(() => {
    replaceUrlParams({
      teacher_tab: stage === "teacher_academy" ? null : stage,
      teacher_subject: subjectId || null,
      teacher_search: search || null,
    });
  }, [search, stage, subjectId]);
  const selectTabFromKeyboard = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === "ArrowLeft" || event.key === "Home" ? "teacher_academy" : "active_teacher";
    setStage(next);
    requestAnimationFrame(() => document.getElementById(`teachers-tab-${next}`)?.focus());
  };
  const closeRemoval = () => {
    if (remove.isPending) return;
    setRemoveTeacher(null);
    setRejectionReason("");
    remove.reset();
  };
  const submitRemoval = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    remove.mutate({
      rejection_reason: String(form.get("rejection_reason") || ""),
      reason_detail: String(form.get("reason_detail") || "").trim(),
    });
  };
  const handleRowClick = (
    event: MouseEvent<HTMLTableRowElement>,
    teacher: RecruitmentTeacher,
  ) => {
    if (isInteractiveTarget(event.target)) return;
    openProfile(teacher, basePath);
  };
  const handleRowKeyboard = (
    event: KeyboardEvent<HTMLTableRowElement>,
    teacher: RecruitmentTeacher,
  ) => {
    if (!teacher.recruitment_candidate_id || isInteractiveTarget(event.target)) return;
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    openProfile(teacher, basePath);
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 xl:flex-row xl:items-end">
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
        <div className="grid w-full shrink-0 gap-2 sm:grid-cols-[13rem_minmax(14rem,20rem)] xl:w-auto">
          <label>
            <span className="sr-only">Filter teachers by subject</span>
            <select
              value={subjectId}
              onChange={(event) => setSubjectId(event.target.value)}
              className={`${fieldClass} min-h-12`}
              aria-label="Filter teachers by subject"
            >
              <option value="">All subjects</option>
              {(options.data?.subjects || []).map((subject) => (
                <option key={subject.id} value={subject.id}>{subject.name}</option>
              ))}
            </select>
          </label>
          <label className="relative">
            <span className="sr-only">Search teachers</span>
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className={`${fieldClass} min-h-12 pl-9`}
              placeholder="Search teachers"
            />
          </label>
        </div>
      </div>
      <div id="teachers-panel" role="tabpanel" aria-labelledby={`teachers-tab-${stage}`}>
        {selected.isLoading ? (
          <div className="overflow-hidden rounded-xl border border-border bg-card" aria-label="Loading teachers">
            <div className="h-12 animate-pulse border-b border-border bg-muted/60 motion-reduce:animate-none" />
            {[0, 1, 2].map((row) => <div key={row} className="h-16 animate-pulse border-b border-border/70 bg-muted/25 last:border-0 motion-reduce:animate-none" />)}
          </div>
        ) : null}
        {selected.error ? <div role="alert" className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">{queryError(selected.error)}</div> : null}
        {!selected.isLoading && !selected.error ? (
          <>
            <ResponsiveTable showAt="lg" ariaLabel={stage === "teacher_academy" ? "Teacher Academy teachers" : "Active teachers"}>
              <table className="w-full min-w-[1080px] table-fixed border-collapse text-left">
                <thead className="sticky top-0 z-10 bg-muted/80 text-[11px] uppercase tracking-wide text-muted-foreground backdrop-blur">
                  <tr>
                    <th scope="col" className="w-[18%] px-4 py-3 font-semibold">Teacher</th>
                    <th scope="col" className="w-[14%] px-3 py-3 font-semibold">{stage === "teacher_academy" ? "Added to Teacher Academy" : "Active since"}</th>
                    <th scope="col" className="w-[15%] px-3 py-3 font-semibold">Position</th>
                    {stage === "teacher_academy" ? (
                      <>
                        <th scope="col" className="w-[12%] px-3 py-3 font-semibold">Academy status</th>
                        <th scope="col" className="w-[20%] px-3 py-3 font-semibold">Progress</th>
                      </>
                    ) : (
                      <>
                        <th scope="col" className="w-[15%] px-3 py-3 font-semibold">Subjects</th>
                        <th scope="col" className="w-[17%] px-3 py-3 font-semibold">Status</th>
                      </>
                    )}
                    <th scope="col" className="w-[15%] px-3 py-3 font-semibold">Account</th>
                    <th scope="col" className="w-16 px-2 py-3 text-center font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {items.map((teacher) => (
                    <tr
                      key={`${teacher.kind}:${teacher.record_id}`}
                      tabIndex={teacher.recruitment_candidate_id ? 0 : -1}
                      onClick={(event) => handleRowClick(event, teacher)}
                      onKeyDown={(event) => handleRowKeyboard(event, teacher)}
                      className={`group bg-card transition-colors duration-150 hover:bg-muted/40 focus:outline-none focus-visible:bg-muted/50 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/30 motion-reduce:transition-none ${
                        teacher.recruitment_candidate_id ? "cursor-pointer" : ""
                      }`}
                    >
                      <td className="px-4 py-3">
                        {teacher.recruitment_candidate_id ? (
                          <a href={profileHref(teacher, basePath)} className="block truncate text-sm font-semibold text-foreground group-hover:text-primary focus:outline-none focus-visible:underline">
                            {teacher.full_name}
                          </a>
                        ) : (
                          <span className="block truncate text-sm font-semibold">{teacher.full_name}</span>
                        )}
                        <span className="mt-0.5 block truncate text-xs text-muted-foreground">{teacher.subject || "Subject not set"}</span>
                      </td>
                      <td className="px-3 py-3 text-xs font-medium text-foreground">
                        {teacher.added_on ? dateLabel(teacher.added_on) : "Not recorded"}
                      </td>
                      <td className="px-3 py-3 text-xs text-foreground">{teacher.position || "Position not set"}</td>
                      {stage === "teacher_academy" ? (
                        <>
                          <td className="px-3 py-3"><AcademyStatus status={teacher.status} /></td>
                          <td className="px-3 py-3"><AcademyProgress teacher={teacher} /></td>
                        </>
                      ) : (
                        <>
                          <td className="px-3 py-3 text-xs text-foreground">{teacher.subject || "Not set"}</td>
                          <td className="px-3 py-3 text-xs font-medium text-foreground">{statusLabel(teacher.status || "active")}</td>
                        </>
                      )}
                      <td className="px-3 py-3"><AccountStatus teacher={teacher} /></td>
                      <td className="px-2 py-2 text-center">
                        <ActionMenu
                          label={`Actions for ${teacher.full_name}`}
                          items={teacherActions(teacher, basePath, setRemoveTeacher)}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!items.length ? <div className="border-t border-border p-8 text-center text-sm text-muted-foreground">No teachers in this view.</div> : null}
            </ResponsiveTable>
            <MobileCardList hideAt="lg">
              {items.map((teacher) => (
                <TeacherMobileCard
                  key={`${teacher.kind}:${teacher.record_id}`}
                  teacher={teacher}
                  basePath={basePath}
                  onRemove={setRemoveTeacher}
                />
              ))}
              {!items.length ? <div className="rounded-xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">No teachers in this view.</div> : null}
            </MobileCardList>
          </>
        ) : null}
      </div>
      <Modal
        open={Boolean(removeTeacher)}
        title="Remove from Teacher Academy"
        subtitle={removeTeacher?.full_name}
        onClose={closeRemoval}
        closeOnOutsideClick={!remove.isPending}
        closeOnEscape={!remove.isPending}
        size="sm"
      >
        <form onSubmit={submitRemoval}>
          <ModalBody className="grid gap-3">
            {remove.error ? (
              <div role="alert" className="rounded-lg border border-destructive/25 bg-destructive/10 p-3 text-xs text-destructive">
                {queryError(remove.error)}
              </div>
            ) : null}
            <label className="text-xs font-semibold">
              Rejection reason
              <select
                autoFocus
                required
                name="rejection_reason"
                value={rejectionReason}
                onChange={(event) => setRejectionReason(event.target.value)}
                className={`${fieldClass} mt-1`}
              >
                <option value="">Select a reason</option>
                {(options.data?.rejection_reason_options || []).map((reason) => (
                  <option key={reason.value} value={reason.value}>{reason.label}</option>
                ))}
              </select>
            </label>
            <label className="text-xs font-semibold">
              Explanation {rejectionReason === "other" ? <span className="text-destructive">(required)</span> : <span className="font-normal text-muted-foreground">(optional)</span>}
              <textarea
                name="reason_detail"
                required={rejectionReason === "other"}
                className={`${fieldClass} mt-1 min-h-24 resize-y`}
                placeholder="Add context for the rejection history"
              />
            </label>
            <p className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs leading-5 text-amber-950">
              The lifecycle profile, Academy lessons, assessments, documents, and audit history will be preserved.
              {removeTeacher?.generated_login_will_be_deleted
                ? " The Academy-generated login will be permanently deleted and must be provisioned again if the teacher is later accepted."
                : ""}
            </p>
          </ModalBody>
          <ModalFooter>
            <div className="flex justify-end gap-2">
              <button type="button" className={secondaryButtonClass} disabled={remove.isPending} onClick={closeRemoval}>Cancel</button>
              <button type="submit" className={`${buttonClass} !bg-destructive !text-destructive-foreground`} disabled={remove.isPending || options.isLoading}>
                {remove.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserMinus className="h-4 w-4" />}
                Remove teacher
              </button>
            </div>
          </ModalFooter>
        </form>
      </Modal>
    </div>
  );
}
