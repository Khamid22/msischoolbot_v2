import { Loader2, RotateCcw, Trash2 } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { jsonBody, recruitmentRequest } from "@/features/recruitment/api";
import { type RecruitmentCandidate } from "@/features/recruitment/model";
import { RECRUITMENT_API, queryError, secondaryButtonClass } from "@/features/recruitment/ui";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";

type Props = {
  candidate: RecruitmentCandidate;
  onAnnouncement: (message: string, tone?: "success" | "error") => void;
};

export function ClosedCandidateActions({ candidate, onAnnouncement }: Props) {
  const queryClient = useQueryClient();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [understood, setUnderstood] = useState(false);
  const restore = useMutation({
    mutationFn: () => recruitmentRequest<{ message: string }>(
      `${RECRUITMENT_API}/candidates/${candidate.id}/restore`,
      { method: "POST", body: jsonBody({ expected_version: candidate.version }) },
    ),
    onSuccess: (result) => {
      onAnnouncement(result.message || "Candidate recovered.");
      void queryClient.invalidateQueries({ queryKey: ["recruitment"] });
    },
    onError: (error) => onAnnouncement(queryError(error), "error"),
  });
  const purge = useMutation({
    mutationFn: () => recruitmentRequest<{ message: string }>(
      `${RECRUITMENT_API}/candidates/${candidate.id}/purge`,
      {
        method: "POST",
        body: jsonBody({
          expected_version: candidate.version,
          confirmation: "PERMANENTLY DELETE",
        }),
      },
    ),
    onSuccess: (result) => {
      setConfirmDelete(false);
      setUnderstood(false);
      onAnnouncement(result.message || "Candidate permanently deleted.");
      void queryClient.invalidateQueries({ queryKey: ["recruitment"] });
    },
    onError: (error) => onAnnouncement(queryError(error), "error"),
  });
  const busy = restore.isPending || purge.isPending;

  return (
    <>
      <div className="flex min-h-11 items-center justify-end gap-1.5">
        <button
          type="button"
          className={`${secondaryButtonClass} min-h-11 px-2.5 text-xs`}
          disabled={busy}
          onClick={() => restore.mutate()}
        >
          {restore.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />}
          Recover
        </button>
        <button
          type="button"
          className="inline-flex min-h-11 items-center gap-1.5 rounded-lg border border-destructive/30 px-2.5 text-xs font-semibold text-destructive hover:bg-destructive/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-destructive/30"
          disabled={busy}
          onClick={() => setConfirmDelete(true)}
        >
          <Trash2 className="h-4 w-4" />
          Delete
        </button>
      </div>

      <Modal
        open={confirmDelete}
        onClose={() => { if (!purge.isPending) { setConfirmDelete(false); setUnderstood(false); } }}
        title="Permanently delete candidate?"
        subtitle={candidate.full_name}
        size="sm"
        closeOnEscape={!purge.isPending}
        closeOnOutsideClick={!purge.isPending}
      >
        <ModalBody className="space-y-3">
          <div role="alert" className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
            This permanently deletes the candidate profile, recruitment history, evaluations, appointments, tasks, decisions, documents, and audit records. It cannot be undone.
          </div>
          <label className="flex min-h-11 cursor-pointer items-start gap-2 rounded-lg border border-border p-3 text-sm">
            <input
              autoFocus
              type="checkbox"
              checked={understood}
              onChange={(event) => setUnderstood(event.target.checked)}
              className="mt-0.5 h-4 w-4"
            />
            <span>I understand that this candidate will be permanently deleted.</span>
          </label>
        </ModalBody>
        <ModalFooter>
          <div className="flex justify-end gap-2">
            <button type="button" className={secondaryButtonClass} disabled={purge.isPending} onClick={() => setConfirmDelete(false)}>Cancel</button>
            <button
              type="button"
              className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-destructive px-4 text-sm font-semibold text-destructive-foreground disabled:opacity-50"
              disabled={!understood || purge.isPending}
              onClick={() => purge.mutate()}
            >
              {purge.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
              Delete permanently
            </button>
          </div>
        </ModalFooter>
      </Modal>
    </>
  );
}
