import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowUpRight,
  Check,
  ClipboardCheck,
  Loader2,
  ShieldCheck,
  X,
} from "lucide-react";
import { useState, type FormEvent } from "react";

import { jsonBody, recruitmentRequest } from "@/features/recruitment/api";
import { dateLabel, type RecruitmentCandidate } from "@/features/recruitment/model";
import {
  RECRUITMENT_API,
  queryError,
  secondaryButtonClass,
} from "@/features/recruitment/ui";
import { routes } from "@/shared/lib/routes";
import { MobileCardList } from "@/shared/ui/MobileCardList";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";
import { ResponsiveTable } from "@/shared/ui/ResponsiveTable";
import { StatusBadge } from "@/shared/ui/StatusBadge";

type PromotionQueueData = {
  items: RecruitmentCandidate[];
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
};

type PromotionReviewResult = {
  message: string;
  candidate: RecruitmentCandidate;
};

type PromotionSelection = {
  candidate: RecruitmentCandidate;
  action: "confirm" | "reject";
};

type TeacherPromotionRequestsProps = {
  onAnnouncement: (message: string, tone?: "success" | "error") => void;
};

function candidateProfileHref(candidateId: number) {
  return `${routes.academicDirectorRecruitment}/candidates/${candidateId}?tab=hiring&origin=teacher-promotions`;
}

export function TeacherPromotionRequests({
  onAnnouncement,
}: TeacherPromotionRequestsProps) {
  const queryClient = useQueryClient();
  const [selection, setSelection] = useState<PromotionSelection | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const promotions = useQuery({
    queryKey: ["recruitment", "promotion-requests"],
    queryFn: () => recruitmentRequest<PromotionQueueData>(
      `${RECRUITMENT_API}/decision-queue?page=1&per_page=100&promotion_only=true`,
    ),
  });

  const review = useMutation({
    mutationFn: ({
      candidateId,
      approvalId,
      status,
      reviewComment,
    }: {
      candidateId: number;
      approvalId: number;
      status: "approved" | "returned";
      reviewComment: string;
    }) => recruitmentRequest<PromotionReviewResult>(
      `${RECRUITMENT_API}/candidates/${candidateId}/approval-requests/${approvalId}/review`,
      {
        method: "POST",
        body: jsonBody({ status, review_comment: reviewComment }),
      },
    ),
    onSuccess: (result, variables) => {
      setSelection(null);
      setRejectionReason("");
      onAnnouncement(
        variables.status === "approved"
          ? result.message || "Promotion confirmed. The teacher is now active."
          : "Promotion request rejected and returned to HR.",
        "success",
      );
      void queryClient.invalidateQueries({ queryKey: ["recruitment", "promotion-requests"] });
      void queryClient.invalidateQueries({ queryKey: ["recruitment", "decision-queue"] });
      void queryClient.invalidateQueries({ queryKey: ["recruitment", "candidates"] });
      void queryClient.invalidateQueries({ queryKey: ["recruitment", "teachers"] });
    },
    onError: (error) => onAnnouncement(queryError(error), "error"),
  });

  const openReview = (
    candidate: RecruitmentCandidate,
    action: PromotionSelection["action"],
  ) => {
    review.reset();
    setRejectionReason("");
    setSelection({ candidate, action });
  };

  const closeReview = () => {
    if (review.isPending) return;
    setSelection(null);
    setRejectionReason("");
    review.reset();
  };

  const submitReview = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const approval = selection?.candidate.actionable_approval;
    if (
      !selection
      || !approval
      || !["requested", "approved"].includes(approval.status)
    ) return;
    const reason = rejectionReason.trim();
    if (selection.action === "reject" && !reason) return;
    review.mutate({
      candidateId: selection.candidate.id,
      approvalId: approval.id,
      status: selection.action === "confirm" ? "approved" : "returned",
      reviewComment: selection.action === "confirm"
        ? "Confirmed and activated by Academic Director."
        : reason,
    });
  };

  const items = promotions.data?.items || [];

  const actionControls = (candidate: RecruitmentCandidate) => {
    const approval = candidate.actionable_approval;
    if (!approval) return null;
    const wasPreviouslyApproved = approval.status === "approved";
    return (
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => openReview(candidate, "confirm")}
          disabled={review.isPending}
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-primary px-3 text-sm font-bold text-primary-foreground transition-colors hover:brightness-105 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none"
        >
          <Check className="h-4 w-4" aria-hidden="true" />
          {wasPreviouslyApproved ? "Complete promotion" : "Confirm"}
        </button>
        {!wasPreviouslyApproved ? (
          <button
            type="button"
            onClick={() => openReview(candidate, "reject")}
            disabled={review.isPending}
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-destructive/35 bg-card px-3 text-sm font-bold text-destructive transition-colors hover:bg-destructive/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-destructive/35 disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none"
          >
            <X className="h-4 w-4" aria-hidden="true" />
            Reject
          </button>
        ) : null}
      </div>
    );
  };

  return (
    <>
      <section
        className="rounded-xl border border-primary/20 bg-primary/[0.035] p-3 sm:p-4"
        aria-labelledby="teacher-promotion-requests-heading"
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-3">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <ShieldCheck className="h-5 w-5" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <h2
                id="teacher-promotion-requests-heading"
                className="text-sm font-black text-foreground"
              >
                Promotion requests
              </h2>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                Review Teacher Academy graduates proposed by HR for Active Teacher status.
              </p>
            </div>
          </div>
          <span className="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-black tabular-nums text-primary">
            {promotions.isLoading
              ? "Loading…"
              : `${items.length} ${items.length === 1 ? "action" : "actions"}`}
          </span>
        </div>

        {promotions.error ? (
          <div
            role="alert"
            className="mt-3 rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
          >
            <p className="font-bold">{queryError(promotions.error)}</p>
            <button
              type="button"
              onClick={() => void promotions.refetch()}
              className="mt-3 inline-flex min-h-11 items-center justify-center rounded-lg border border-destructive/30 bg-card px-3 font-bold focus:outline-none focus-visible:ring-2 focus-visible:ring-destructive/35"
            >
              Try again
            </button>
          </div>
        ) : null}

        {promotions.isLoading ? (
          <div
            role="status"
            className="mt-3 flex min-h-20 items-center justify-center gap-2 rounded-xl border border-dashed border-border bg-card text-sm font-semibold text-muted-foreground"
          >
            <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />
            Loading promotion requests…
          </div>
        ) : null}

        {!promotions.isLoading && !promotions.error && !items.length ? (
          <p className="mt-3 rounded-xl border border-dashed border-border bg-card px-3 py-4 text-sm text-muted-foreground">
            No Teacher Academy promotion requests need review.
          </p>
        ) : null}

        {!promotions.isLoading && !promotions.error && items.length ? (
          <>
            <ResponsiveTable
              showAt="md"
              className="mt-3"
              ariaLabel="Teacher promotion requests"
            >
              <table className="w-full min-w-[56rem] border-collapse text-left text-sm">
                <thead className="bg-muted/65 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 font-black">Teacher</th>
                    <th className="px-3 py-2 font-black">Subject / position</th>
                    <th className="px-3 py-2 font-black">HR request</th>
                    <th className="px-3 py-2 font-black">Status</th>
                    <th className="px-3 py-2 font-black">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {items.map((candidate) => {
                    const approval = candidate.actionable_approval;
                    const isConfirmed = approval?.status === "approved";
                    return (
                      <tr key={`${candidate.id}:${approval?.id}`} className="align-top">
                        <td className="px-3 py-3">
                          <a
                            href={candidateProfileHref(candidate.id)}
                            className="inline-flex min-h-11 items-center gap-1 font-black text-foreground hover:text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
                          >
                            {candidate.full_name}
                            <ArrowUpRight className="h-4 w-4 shrink-0" aria-hidden="true" />
                          </a>
                        </td>
                        <td className="px-3 py-3">
                          <p className="font-semibold text-foreground">
                            {candidate.subject || "Subject not set"}
                          </p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {candidate.applied_position || "Teacher"}
                          </p>
                        </td>
                        <td className="max-w-sm px-3 py-3">
                          <p className="line-clamp-2 text-xs leading-5 text-foreground">
                            {approval?.request_note || "No note provided by HR."}
                          </p>
                          <p className="mt-1 text-[0.6875rem] text-muted-foreground">
                            Requested {dateLabel(approval?.created_at)}
                          </p>
                        </td>
                        <td className="px-3 py-3">
                          <StatusBadge
                            status={isConfirmed ? "approved" : "requested"}
                            tone={isConfirmed ? "success" : "warning"}
                          >
                            {isConfirmed ? "Ready to activate" : "Needs review"}
                          </StatusBadge>
                        </td>
                        <td className="px-3 py-3">{actionControls(candidate)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </ResponsiveTable>

            <MobileCardList hideAt="md" className="mt-3">
              {items.map((candidate) => {
                const approval = candidate.actionable_approval;
                const isConfirmed = approval?.status === "approved";
                return (
                  <article
                    key={`${candidate.id}:${approval?.id}`}
                    className="rounded-xl border border-border bg-card p-3 shadow-sm"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <a
                          href={candidateProfileHref(candidate.id)}
                          className="inline-flex min-h-11 items-center gap-1 font-black text-foreground hover:text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
                        >
                          <span className="truncate">{candidate.full_name}</span>
                          <ArrowUpRight className="h-4 w-4 shrink-0" aria-hidden="true" />
                        </a>
                        <p className="text-xs text-muted-foreground">
                          {candidate.subject || candidate.applied_position || "Subject not set"}
                        </p>
                      </div>
                      <StatusBadge
                        status={isConfirmed ? "approved" : "requested"}
                        tone={isConfirmed ? "success" : "warning"}
                      >
                        {isConfirmed ? "Ready to activate" : "Needs review"}
                      </StatusBadge>
                    </div>
                    <div className="mt-2 rounded-lg bg-muted/55 p-3">
                      <p className="text-xs leading-5 text-foreground">
                        {approval?.request_note || "No note provided by HR."}
                      </p>
                      <p className="mt-1 text-[0.6875rem] text-muted-foreground">
                        Requested {dateLabel(approval?.created_at)}
                      </p>
                    </div>
                    <div className="mt-3">{actionControls(candidate)}</div>
                  </article>
                );
              })}
            </MobileCardList>
          </>
        ) : null}
      </section>

      <Modal
        open={Boolean(selection)}
        title={
          selection?.action === "confirm"
            ? selection.candidate.actionable_approval?.status === "approved"
              ? "Complete promotion"
              : "Confirm promotion"
            : "Reject promotion request"
        }
        subtitle={selection?.candidate.full_name}
        onClose={closeReview}
        closeOnOutsideClick={!review.isPending}
        closeOnEscape={!review.isPending}
        initialFocusSelector="[data-promotion-submit]"
        size="sm"
      >
        <form onSubmit={submitReview}>
          <ModalBody className="grid gap-3">
            {review.error ? (
              <div
                role="alert"
                className="rounded-lg border border-destructive/25 bg-destructive/10 p-3 text-sm text-destructive"
              >
                {queryError(review.error)}
              </div>
            ) : null}
            {selection?.action === "reject" ? (
              <label className="text-sm font-bold text-foreground">
                Reason for rejection
                <textarea
                  required
                  maxLength={5000}
                  value={rejectionReason}
                  onChange={(event) => setRejectionReason(event.target.value)}
                  className="mt-1 min-h-28 w-full resize-y rounded-lg border border-border bg-background px-3 py-2 text-sm font-normal outline-none focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/20"
                  placeholder="Explain what HR should correct or review"
                />
              </label>
            ) : (
              <div className="flex items-start gap-3 rounded-xl border border-primary/20 bg-primary/5 p-3">
                <ClipboardCheck className="mt-0.5 h-5 w-5 shrink-0 text-primary" aria-hidden="true" />
                <p className="text-sm leading-6 text-foreground">
                  This immediately moves the teacher from Teacher Academy to Active Teachers. No
                  additional approval step is required.
                </p>
              </div>
            )}
            {selection?.action === "reject" ? (
              <p className="rounded-lg border border-destructive/25 bg-destructive/10 p-3 text-xs leading-5 text-destructive">
                The request will return to HR. The Teacher Academy record and its history will be
                preserved.
              </p>
            ) : null}
          </ModalBody>
          <ModalFooter>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                className={`${secondaryButtonClass} min-h-11`}
                disabled={review.isPending}
                onClick={closeReview}
              >
                Cancel
              </button>
              <button
                type="submit"
                data-promotion-submit
                disabled={
                  review.isPending
                  || (selection?.action === "reject" && !rejectionReason.trim())
                }
                className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 text-sm font-black transition-colors focus:outline-none focus-visible:ring-2 disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none ${
                  selection?.action === "reject"
                    ? "bg-destructive text-destructive-foreground hover:brightness-105 focus-visible:ring-destructive/35"
                    : "bg-primary text-primary-foreground hover:brightness-105 focus-visible:ring-primary/40"
                }`}
              >
                {review.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />
                ) : selection?.action === "reject" ? (
                  <X className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <Check className="h-4 w-4" aria-hidden="true" />
                )}
                {selection?.action === "reject"
                  ? "Reject request"
                  : selection?.candidate.actionable_approval?.status === "approved"
                    ? "Activate teacher"
                    : "Confirm and activate"}
              </button>
            </div>
          </ModalFooter>
        </form>
      </Modal>
    </>
  );
}
