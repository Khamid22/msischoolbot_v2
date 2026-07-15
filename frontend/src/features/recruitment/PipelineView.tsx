import { Ban, Clock3, Loader2, UserMinus } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";

import { recruitmentRequest, jsonBody } from "@/features/recruitment/api";
import {
  alternativeStages,
  dateLabel,
  manualStages,
  primaryStages,
  stageLabels,
  type RecruitmentCandidate,
  type RecruitmentOptions,
  type RecruitmentRole,
} from "@/features/recruitment/model";
import { RECRUITMENT_API, EmptyLine, PageState, buttonClass, fieldClass, queryError, rememberRecruitmentReturn, replaceUrlParams, restoreRecruitmentReturn, secondaryButtonClass } from "@/features/recruitment/ui";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";

type PipelineData = {
  stages: Record<string, RecruitmentCandidate[]>;
  counts: Record<string, number>;
  total: number;
};

type MutationPayload = { message: string; candidate?: RecruitmentCandidate };
type OutcomeDecision = "rejected" | "on_hold" | "candidate_withdrew";
type OutcomeSelection = { candidate: RecruitmentCandidate; decision: OutcomeDecision };
const allStages = [...primaryStages, ...alternativeStages];

const outcomeDetails: Record<OutcomeDecision, { label: string; icon: ReactNode; tone: string }> = {
  rejected: { label: "Reject", icon: <Ban className="h-4 w-4" />, tone: "hover:border-destructive/60 hover:bg-destructive/10" },
  on_hold: { label: "On Hold", icon: <Clock3 className="h-4 w-4" />, tone: "hover:border-amber-500/60 hover:bg-amber-500/10" },
  candidate_withdrew: { label: "Withdraw", icon: <UserMinus className="h-4 w-4" />, tone: "hover:border-muted-foreground/50 hover:bg-muted" },
};

function OutcomeDialog({
  selection,
  options,
  busy,
  onClose,
  onSubmit,
}: {
  selection: OutcomeSelection | null;
  options?: RecruitmentOptions;
  busy: boolean;
  onClose: () => void;
  onSubmit: (values: Record<string, string | null>) => void;
}) {
  const [rejectionReason, setRejectionReason] = useState("");
  const [reasonDetail, setReasonDetail] = useState("");
  const [followUpAt, setFollowUpAt] = useState("");
  useEffect(() => {
    setRejectionReason("");
    setReasonDetail("");
    setFollowUpAt("");
  }, [selection]);
  if (!selection) return null;
  const { candidate, decision } = selection;
  const detail = outcomeDetails[decision];
  const reasons = options?.rejection_reason_options?.length
    ? options.rejection_reason_options
    : (options?.rejection_reasons || []).map((value) => ({ value, label: value.replace(/_/g, " ") }));
  const needsDetail = decision === "on_hold" || (decision === "rejected" && rejectionReason === "other");
  const invalid = (decision === "rejected" && !rejectionReason) || (needsDetail && !reasonDetail.trim());
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (invalid) return;
    onSubmit({
      decision,
      rejection_reason: decision === "rejected" ? rejectionReason : "",
      reason_detail: reasonDetail.trim(),
      follow_up_at: decision === "on_hold" ? followUpAt || null : null,
    });
  };
  return (
    <Modal open onClose={onClose} title={`${detail.label} candidate`} subtitle={candidate.full_name} size="sm">
      <form onSubmit={submit}>
        <ModalBody className="grid gap-3">
          {decision === "rejected" ? (
            <label className="text-xs font-semibold">
              Rejection reason
              <select autoFocus required value={rejectionReason} onChange={(event) => setRejectionReason(event.target.value)} className={`${fieldClass} mt-1`}>
                <option value="">Select a reason</option>
                {reasons.map((reason) => <option key={reason.value} value={reason.value}>{reason.label}</option>)}
              </select>
            </label>
          ) : null}
          <label className="text-xs font-semibold">
            Reason / explanation
            <textarea autoFocus={decision !== "rejected"} required={needsDetail} value={reasonDetail} onChange={(event) => setReasonDetail(event.target.value)} className={`${fieldClass} mt-1 min-h-24`} />
          </label>
          {decision === "on_hold" ? (
            <label className="text-xs font-semibold">
              Follow-up date
              <input type="datetime-local" value={followUpAt} onChange={(event) => setFollowUpAt(event.target.value)} className={`${fieldClass} mt-1`} />
            </label>
          ) : null}
        </ModalBody>
        <ModalFooter>
          <div className="flex justify-end gap-2">
            <button type="button" className={secondaryButtonClass} disabled={busy} onClick={onClose}>Cancel</button>
            <button type="submit" className={buttonClass} disabled={busy || invalid}>
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : detail.icon}
              Confirm
            </button>
          </div>
        </ModalFooter>
      </form>
    </Modal>
  );
}

function CandidateCard({
  candidate,
  basePath,
  onDragStart,
  onDragEnd,
}: {
  candidate: RecruitmentCandidate;
  basePath: string;
  onDragStart: (candidate: RecruitmentCandidate) => void;
  onDragEnd: () => void;
}) {
  const canMove = Boolean(candidate.permissions?.can_move_stage) && !["teacher_academy", "active_teacher"].includes(candidate.status);

  return (
    <article
      draggable={canMove}
      onDragStart={(event) => {
        if (!canMove) {
          event.preventDefault();
          return;
        }
        event.dataTransfer.setData("text/plain", String(candidate.id));
        event.dataTransfer.effectAllowed = "move";
        onDragStart(candidate);
      }}
      onDragEnd={onDragEnd}
      className={`rounded-lg border border-border bg-card shadow-sm transition-colors hover:border-primary/30 focus-within:ring-2 focus-within:ring-primary/25 ${canMove ? "cursor-grab active:cursor-grabbing" : ""}`}
    >
      <a
        href={`${basePath}/candidates/${candidate.id}?tab=overview&origin=pipeline`}
        onClick={() => rememberRecruitmentReturn("pipeline")}
        className="block min-h-20 rounded-lg px-3 py-3 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/30"
        title={candidate.full_name}
      >
        <p className="truncate text-sm font-semibold text-foreground">{candidate.full_name}</p>
        <p className="mt-1 truncate text-xs text-muted-foreground">
          {candidate.applied_position || candidate.subject || "Position not set"}
        </p>
        {candidate.next_task ? (
          <div className="mt-2 flex items-center justify-between gap-2 rounded-md bg-muted/60 px-2 py-1.5 text-xs">
            <span className="min-w-0 truncate font-medium text-foreground">{candidate.next_task.title}</span>
            <span className="shrink-0 text-muted-foreground">{dateLabel(candidate.next_task.due_at)}</span>
          </div>
        ) : null}
      </a>
    </article>
  );
}

export function PipelineView({
  basePath,
  role,
  options,
  onAnnouncement,
}: {
  basePath: string;
  role: RecruitmentRole;
  options?: RecruitmentOptions;
  onAnnouncement: (message: string) => void;
}) {
  const queryClient = useQueryClient();
  const initialStage = new URLSearchParams(window.location.search).get("stage") || primaryStages[0];
  const [mobileStage, setMobileStage] = useState((allStages as readonly string[]).includes(initialStage) ? initialStage : primaryStages[0]);
  const [dragOverStage, setDragOverStage] = useState<string | null>(null);
  const [draggedCandidate, setDraggedCandidate] = useState<RecruitmentCandidate | null>(null);
  const [dragOverOutcome, setDragOverOutcome] = useState<OutcomeDecision | null>(null);
  const [outcomeSelection, setOutcomeSelection] = useState<OutcomeSelection | null>(null);
  const draggedCandidateRef = useRef<RecruitmentCandidate | null>(null);
  const pipeline = useQuery({
    queryKey: ["recruitment", "pipeline"],
    queryFn: () => recruitmentRequest<PipelineData>(`${RECRUITMENT_API}/pipeline`),
  });
  const move = useMutation({
    mutationFn: ({ candidate, stage }: { candidate: RecruitmentCandidate; stage: string }) =>
      recruitmentRequest<MutationPayload>(`${RECRUITMENT_API}/candidates/${candidate.id}/stage`, {
        method: "POST",
        body: jsonBody({ stage, expected_version: candidate.version, reason: "Pipeline move" }),
      }),
    onMutate: async ({ candidate, stage }) => {
      await queryClient.cancelQueries({ queryKey: ["recruitment", "pipeline"] });
      const previous = queryClient.getQueryData<PipelineData>(["recruitment", "pipeline"]);
      if (previous) {
        const stages = Object.fromEntries(
          Object.entries(previous.stages).map(([key, values]) => [key, values.filter((item) => item.id !== candidate.id)]),
        );
        stages[stage] = [{ ...candidate, status: stage, version: candidate.version + 1 }, ...(stages[stage] || [])];
        queryClient.setQueryData(["recruitment", "pipeline"], { ...previous, stages });
      }
      return { previous };
    },
    onError: (error, _variables, context) => {
      if (context?.previous) queryClient.setQueryData(["recruitment", "pipeline"], context.previous);
      onAnnouncement(`Move failed. ${queryError(error)}`);
    },
    onSuccess: (result) => onAnnouncement(result.message || "Candidate moved."),
    onSettled: () => void queryClient.invalidateQueries({ queryKey: ["recruitment"] }),
  });
  const outcome = useMutation({
    mutationFn: ({ candidate, values }: { candidate: RecruitmentCandidate; values: Record<string, string | null> }) =>
      recruitmentRequest<MutationPayload>(`${RECRUITMENT_API}/candidates/${candidate.id}/final-decisions`, {
        method: "POST",
        body: jsonBody(values),
      }),
    onSuccess: (result) => {
      setOutcomeSelection(null);
      onAnnouncement(result.message || "Candidate outcome recorded.");
    },
    onError: (error) => onAnnouncement(queryError(error)),
    onSettled: () => void queryClient.invalidateQueries({ queryKey: ["recruitment"] }),
  });

  useEffect(() => {
    if (pipeline.data) restoreRecruitmentReturn("pipeline");
  }, [pipeline.data]);

  if (pipeline.isLoading) return <PageState>Loading recruitment pipeline…</PageState>;
  if (pipeline.error || !pipeline.data) return <PageState tone="error">{queryError(pipeline.error)}</PageState>;
  const cards = (items: RecruitmentCandidate[]) => (
    <div className="space-y-2">
      {items.map((candidate) => (
        <CandidateCard
          key={candidate.id}
          candidate={candidate}
          basePath={basePath}
          onDragStart={(draggedCandidate) => {
            draggedCandidateRef.current = draggedCandidate;
            setDraggedCandidate(draggedCandidate);
          }}
          onDragEnd={() => {
            draggedCandidateRef.current = null;
            setDraggedCandidate(null);
            setDragOverStage(null);
            setDragOverOutcome(null);
          }}
        />
      ))}
      {!items.length ? <EmptyLine>No candidates in this stage.</EmptyLine> : null}
    </div>
  );

  return (
    <div className="space-y-3">
      <div className="md:hidden">
        <label className="text-xs font-semibold text-muted-foreground">
          Pipeline stage
          <select
            className={`${fieldClass} mt-1`}
            value={mobileStage}
            onChange={(event) => {
              setMobileStage(event.target.value);
              replaceUrlParams({ stage: event.target.value });
            }}
          >
            <optgroup label="Recruitment stages">
              {primaryStages.map((stage) => <option key={stage} value={stage}>{stageLabels[stage]} · {pipeline.data.counts[stage] || 0}</option>)}
            </optgroup>
            <optgroup label="Alternative outcomes">
              {alternativeStages.map((stage) => <option key={stage} value={stage}>{stageLabels[stage]} · {pipeline.data.counts[stage] || 0}</option>)}
            </optgroup>
          </select>
        </label>
        <section aria-label={`${stageLabels[mobileStage]} candidates`} className="mt-3 rounded-xl border border-border bg-muted/25 p-2.5">
          <div className="mb-2 flex min-h-11 items-center justify-between gap-2 px-1">
            <h2 className="text-xs font-semibold uppercase tracking-wide">{stageLabels[mobileStage]}</h2>
            <span className="rounded-full bg-card px-2 py-1 text-xs font-semibold tabular-nums">{pipeline.data.counts[mobileStage] || 0}</span>
          </div>
          {cards(pipeline.data.stages[mobileStage] || [])}
        </section>
      </div>

      <div className="hidden overflow-x-auto pb-1 md:block">
        <div className="grid min-w-[1230px] grid-cols-6 gap-2">
          {primaryStages.map((stage) => {
            const acceptsDrop = manualStages.includes(stage as (typeof manualStages)[number]);
            const items = pipeline.data.stages[stage] || [];
            const highlighted = dragOverStage === stage;
            return (
              <section
                key={stage}
                aria-label={`${stageLabels[stage]} candidates`}
                onDragEnter={(event) => {
                  if (acceptsDrop && draggedCandidateRef.current) {
                    event.preventDefault();
                    setDragOverStage(stage);
                  }
                }}
                onDragOver={(event) => {
                  if (acceptsDrop && draggedCandidateRef.current) event.preventDefault();
                }}
                onDragLeave={(event) => {
                  if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragOverStage(null);
                }}
                onDrop={(event) => {
                  setDragOverStage(null);
                  if (!acceptsDrop) return;
                  event.preventDefault();
                  const candidate = draggedCandidateRef.current;
                  draggedCandidateRef.current = null;
                  setDraggedCandidate(null);
                  if (candidate && candidate.status !== stage) move.mutate({ candidate, stage });
                }}
                className={`min-h-60 rounded-xl border p-2 transition-colors motion-reduce:transition-none ${
                  highlighted ? "border-primary bg-primary/5 ring-2 ring-primary/15" : "border-border bg-muted/25"
                }`}
              >
                <div className="mb-2 flex min-h-11 items-center justify-between gap-2 px-1">
                  <h2 className="text-[11px] font-semibold uppercase tracking-wide text-foreground">{stageLabels[stage]}</h2>
                  <span className="rounded-full bg-card px-2 py-1 text-[11px] font-semibold text-muted-foreground tabular-nums">{items.length}</span>
                </div>
                {cards(items)}
              </section>
            );
          })}
        </div>
      </div>

      {draggedCandidate ? (
        <section aria-label="Candidate outcome drop targets" className="rounded-xl border border-dashed border-primary/30 bg-card/60 p-2 backdrop-blur">
          <div className="grid gap-2 sm:grid-cols-3">
            {(["rejected", "on_hold", "candidate_withdrew"] as OutcomeDecision[]).map((decision) => {
              const permitted = decision === "rejected"
                ? Boolean(draggedCandidate.permissions?.can_reject)
                : role === "hr_manager" || role === "ceo";
              if (!permitted) return null;
              const detail = outcomeDetails[decision];
              const highlighted = dragOverOutcome === decision;
              return (
                <div
                  key={decision}
                  onDragEnter={(event) => {
                    event.preventDefault();
                    setDragOverOutcome(decision);
                  }}
                  onDragOver={(event) => event.preventDefault()}
                  onDragLeave={() => setDragOverOutcome(null)}
                  onDrop={(event) => {
                    event.preventDefault();
                    const candidate = draggedCandidateRef.current;
                    draggedCandidateRef.current = null;
                    setDraggedCandidate(null);
                    setDragOverOutcome(null);
                    if (candidate) setOutcomeSelection({ candidate, decision });
                  }}
                  className={`flex min-h-16 items-center justify-center gap-2 rounded-lg border border-dashed px-3 text-sm font-semibold transition-colors motion-reduce:transition-none ${detail.tone} ${highlighted ? "border-primary bg-primary/10 ring-2 ring-primary/20" : "border-border bg-background/50 text-muted-foreground"}`}
                >
                  {detail.icon}
                  {detail.label}
                </div>
              );
            })}
          </div>
        </section>
      ) : (
        <section aria-label="Alternative outcomes" className="overflow-hidden rounded-xl border border-border bg-card">
          <div className="grid sm:grid-cols-3 sm:divide-x sm:divide-border">
            {alternativeStages.map((stage) => (
              <a
                key={stage}
                href={`${basePath}/candidates?stage=${stage}`}
                className="flex min-h-11 items-center justify-between border-b border-border px-3 text-[13px] font-semibold transition-colors last:border-b-0 hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/30 sm:border-b-0"
              >
                <span>{stageLabels[stage]}</span>
                <span className="rounded-full bg-muted px-2 py-0.5 text-xs tabular-nums">{pipeline.data.counts[stage] || 0}</span>
              </a>
            ))}
          </div>
        </section>
      )}

      <OutcomeDialog
        selection={outcomeSelection}
        options={options}
        busy={outcome.isPending}
        onClose={() => {
          if (!outcome.isPending) setOutcomeSelection(null);
        }}
        onSubmit={(values) => {
          if (outcomeSelection) outcome.mutate({ candidate: outcomeSelection.candidate, values });
        }}
      />

    </div>
  );
}
