import { ArrowRightLeft, Eye, GripVertical } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { recruitmentRequest, jsonBody } from "@/features/recruitment/api";
import {
  alternativeStages,
  dateLabel,
  manualStages,
  primaryStages,
  stageLabels,
  type RecruitmentCandidate,
} from "@/features/recruitment/model";
import { RECRUITMENT_API, EmptyLine, PageState, buttonClass, fieldClass, queryError, rememberRecruitmentReturn, replaceUrlParams, restoreRecruitmentReturn, secondaryButtonClass } from "@/features/recruitment/ui";
import { ActionMenu, type ActionMenuItem } from "@/shared/ui/ActionMenu";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";

type PipelineData = {
  stages: Record<string, RecruitmentCandidate[]>;
  counts: Record<string, number>;
  total: number;
};

type MutationPayload = { message: string; candidate?: RecruitmentCandidate };
const allStages = [...primaryStages, ...alternativeStages];

function MoveCandidateDialog({
  candidate,
  busy,
  onClose,
  onMove,
}: {
  candidate: RecruitmentCandidate | null;
  busy: boolean;
  onClose: () => void;
  onMove: (stage: string) => void;
}) {
  const [stage, setStage] = useState("");
  useEffect(() => setStage(""), [candidate]);
  return (
    <Modal
      open={Boolean(candidate)}
      onClose={onClose}
      title="Move candidate"
      subtitle={candidate ? `${candidate.full_name} · ${stageLabels[candidate.status] || candidate.status}` : undefined}
      size="sm"
      initialFocusSelector="#move-candidate-stage"
    >
      <ModalBody>
        <label className="text-xs font-semibold text-foreground">
          New stage
          <select id="move-candidate-stage" value={stage} onChange={(event) => setStage(event.target.value)} className={`${fieldClass} mt-1`}>
            <option value="">Choose a stage</option>
            {manualStages.filter((item) => item !== candidate?.status).map((item) => (
              <option key={item} value={item}>{stageLabels[item]}</option>
            ))}
          </select>
        </label>
        <p className="mt-3 text-xs leading-5 text-muted-foreground">
          Academy and Active Teacher outcomes continue through the protected approval workflow.
        </p>
      </ModalBody>
      <ModalFooter>
        <div className="flex justify-end gap-2">
          <button type="button" className={secondaryButtonClass} onClick={onClose}>Cancel</button>
          <button type="button" className={buttonClass} disabled={!stage || busy} onClick={() => onMove(stage)}>
            <ArrowRightLeft className="h-4 w-4" /> Move
          </button>
        </div>
      </ModalFooter>
    </Modal>
  );
}

function CandidateCard({
  candidate,
  basePath,
  onMoveRequested,
}: {
  candidate: RecruitmentCandidate;
  basePath: string;
  onMoveRequested: (candidate: RecruitmentCandidate) => void;
}) {
  const canMove = Boolean(candidate.permissions?.can_move_stage) && !["teacher_academy", "active_teacher"].includes(candidate.status);
  const items: ActionMenuItem[] = [
    {
      key: "view",
      label: "View profile",
      icon: <Eye className="h-4 w-4" />,
      onClick: () => {
        rememberRecruitmentReturn("pipeline");
        window.location.assign(`${basePath}/candidates/${candidate.id}?tab=overview&origin=pipeline`);
      },
    },
  ];
  if (canMove) {
    items.push({
      key: "move",
      label: "Move candidate",
      icon: <ArrowRightLeft className="h-4 w-4" />,
      onClick: () => onMoveRequested(candidate),
    });
  }

  return (
    <article className="rounded-lg border border-border bg-card px-2.5 py-2 shadow-sm transition-colors hover:border-primary/30 focus-within:ring-2 focus-within:ring-primary/25">
      <div className="flex items-start gap-1">
        {canMove ? (
          <button
            type="button"
            draggable
            onDragStart={(event) => {
              event.dataTransfer.setData("application/x-msi-recruitment", JSON.stringify({ id: candidate.id, version: candidate.version }));
              event.dataTransfer.effectAllowed = "move";
            }}
            className="hidden h-11 w-11 shrink-0 cursor-grab items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 active:cursor-grabbing lg:flex"
            aria-label={`Drag ${candidate.full_name}`}
            title="Drag to another stage"
          >
            <GripVertical className="h-4 w-4" />
          </button>
        ) : null}
        <div className="min-w-0 flex-1 py-1.5">
          <a
            href={`${basePath}/candidates/${candidate.id}?tab=overview&origin=pipeline`}
            onClick={() => rememberRecruitmentReturn("pipeline")}
            className="flex min-h-11 items-center truncate rounded text-sm font-semibold text-foreground hover:text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
            title={candidate.full_name}
          >
            {candidate.full_name}
          </a>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {candidate.applied_position || candidate.subject || "Position not set"}
          </p>
        </div>
        <ActionMenu items={items} label={`Actions for ${candidate.full_name}`} />
      </div>
      {candidate.next_task ? (
        <div className="mt-1.5 flex items-center justify-between gap-2 rounded-md bg-muted/60 px-2 py-1.5 text-xs">
          <span className="min-w-0 truncate font-medium text-foreground">{candidate.next_task.title}</span>
          <span className="shrink-0 text-muted-foreground">{dateLabel(candidate.next_task.due_at)}</span>
        </div>
      ) : null}
    </article>
  );
}

export function PipelineView({ basePath, onAnnouncement }: { basePath: string; onAnnouncement: (message: string) => void }) {
  const queryClient = useQueryClient();
  const initialStage = new URLSearchParams(window.location.search).get("stage") || primaryStages[0];
  const [mobileStage, setMobileStage] = useState((allStages as readonly string[]).includes(initialStage) ? initialStage : primaryStages[0]);
  const [moveCandidate, setMoveCandidate] = useState<RecruitmentCandidate | null>(null);
  const [dragOverStage, setDragOverStage] = useState<string | null>(null);
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
      setMoveCandidate(null);
      return { previous };
    },
    onError: (error, _variables, context) => {
      if (context?.previous) queryClient.setQueryData(["recruitment", "pipeline"], context.previous);
      onAnnouncement(`Move failed. ${queryError(error)}`);
    },
    onSuccess: (result) => onAnnouncement(result.message || "Candidate moved."),
    onSettled: () => void queryClient.invalidateQueries({ queryKey: ["recruitment"] }),
  });

  const candidatesById = useMemo(() => {
    const values = Object.values(pipeline.data?.stages || {}).flat();
    return new Map(values.map((candidate) => [candidate.id, candidate]));
  }, [pipeline.data]);

  useEffect(() => {
    if (pipeline.data) restoreRecruitmentReturn("pipeline");
  }, [pipeline.data]);

  if (pipeline.isLoading) return <PageState>Loading recruitment pipeline…</PageState>;
  if (pipeline.error || !pipeline.data) return <PageState tone="error">{queryError(pipeline.error)}</PageState>;
  const sample = Object.values(pipeline.data.stages).flat()[0];
  const canMove = Boolean(sample?.permissions?.can_move_stage);

  const cards = (items: RecruitmentCandidate[]) => (
    <div className="space-y-2">
      {items.map((candidate) => (
        <CandidateCard key={candidate.id} candidate={candidate} basePath={basePath} onMoveRequested={setMoveCandidate} />
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
            const acceptsDrop = canMove && manualStages.includes(stage as (typeof manualStages)[number]);
            const items = pipeline.data.stages[stage] || [];
            const highlighted = dragOverStage === stage;
            return (
              <section
                key={stage}
                aria-label={`${stageLabels[stage]} candidates`}
                onDragEnter={(event) => {
                  if (acceptsDrop) {
                    event.preventDefault();
                    setDragOverStage(stage);
                  }
                }}
                onDragOver={(event) => {
                  if (acceptsDrop) event.preventDefault();
                }}
                onDragLeave={(event) => {
                  if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragOverStage(null);
                }}
                onDrop={(event) => {
                  setDragOverStage(null);
                  if (!acceptsDrop) return;
                  event.preventDefault();
                  try {
                    const value = JSON.parse(event.dataTransfer.getData("application/x-msi-recruitment"));
                    const candidate = candidatesById.get(Number(value.id));
                    if (candidate && candidate.status !== stage) move.mutate({ candidate, stage });
                  } catch {
                    onAnnouncement("The dragged candidate could not be read.");
                  }
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

      <MoveCandidateDialog
        candidate={moveCandidate}
        busy={move.isPending}
        onClose={() => setMoveCandidate(null)}
        onMove={(stage) => {
          if (moveCandidate) move.mutate({ candidate: moveCandidate, stage });
        }}
      />
    </div>
  );
}
