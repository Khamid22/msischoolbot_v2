import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Clock3, Loader2, Play, XCircle } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { jsonBody, recruitmentRequest } from "@/features/recruitment/api";
import { dateTimeLabel, type RecruitmentAppointment, type RecruitmentCandidate } from "@/features/recruitment/model";
import { RECRUITMENT_API, buttonClass, fieldClass, queryError, secondaryButtonClass } from "@/features/recruitment/ui";
import type { FloatingToastTone } from "@/shared/ui/FloatingToast";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";

type SessionResponse = { message: string; candidate?: RecruitmentCandidate; appointment?: RecruitmentAppointment | null };

function elapsedLabel(startedAt?: string, now = Date.now()) {
  if (!startedAt) return "00:00";
  const seconds = Math.max(0, Math.floor((now - new Date(startedAt).getTime()) / 1000));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainder = seconds % 60;
  return `${hours ? `${String(hours).padStart(2, "0")}:` : ""}${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
}

export function InterviewSessionModal({
  candidate,
  appointment,
  open,
  onClose,
  onAnnouncement,
}: {
  candidate: RecruitmentCandidate;
  appointment: RecruitmentAppointment;
  open: boolean;
  onClose: () => void;
  onAnnouncement: (message: string, tone?: FloatingToastTone) => void;
}) {
  const queryClient = useQueryClient();
  const [session, setSession] = useState(appointment);
  const [now, setNow] = useState(Date.now());
  const [confirmFail, setConfirmFail] = useState(false);
  const notesRef = useRef<HTMLTextAreaElement>(null);
  useEffect(() => { setSession(appointment); setConfirmFail(false); }, [appointment]);
  useEffect(() => {
    if (!open) return undefined;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [open, session.status]);
  const startAvailable = useMemo(() => {
    const boundary = new Date(session.start_available_at || "").getTime();
    return session.can_start || (Number.isFinite(boundary) && now >= boundary);
  }, [now, session.can_start, session.start_available_at]);
  const start = useMutation({
    mutationFn: () => recruitmentRequest<SessionResponse>(`${RECRUITMENT_API}/candidates/${candidate.id}/appointments/${session.id}/start-interview`, { method: "POST", body: jsonBody({ expected_version: session.version }) }),
    onSuccess: (result) => { if (result.appointment) setSession(result.appointment); onAnnouncement(result.message || "Interview started."); void queryClient.invalidateQueries({ queryKey: ["recruitment"] }); },
    onError: (error) => onAnnouncement(queryError(error), "error"),
  });
  const complete = useMutation({
    mutationFn: ({ result, notes }: { result: "passed" | "failed"; notes: string }) => recruitmentRequest<SessionResponse>(`${RECRUITMENT_API}/candidates/${candidate.id}/appointments/${session.id}/complete-interview`, { method: "POST", body: jsonBody({ expected_version: session.version, result, notes }) }),
    onSuccess: (result) => { onAnnouncement(result.message || "Interview completed."); void queryClient.invalidateQueries({ queryKey: ["recruitment"] }); onClose(); },
    onError: (error) => onAnnouncement(queryError(error), "error"),
  });
  const pending = start.isPending || complete.isPending;
  const inProgress = session.status === "in_progress";

  return (
    <Modal open={open} onClose={() => { if (!pending) onClose(); }} title={inProgress ? "Conduct job interview" : "Job interview"} subtitle={candidate.full_name} size="md" closeOnEscape={!pending} closeOnOutsideClick={!pending}>
      <form className="flex min-h-0 flex-1 flex-col" onSubmit={(event) => { event.preventDefault(); const data = new FormData(event.currentTarget); complete.mutate({ result: "passed", notes: String(data.get("notes") || "") }); }}>
        <ModalBody className="space-y-4">
          <section className="grid gap-2 rounded-xl border border-border bg-muted/35 p-3 sm:grid-cols-3">
            <div><span className="text-[10px] font-semibold uppercase text-muted-foreground">{inProgress ? "Actual start" : "Scheduled"}</span><strong className="mt-1 block text-sm">{dateTimeLabel(inProgress ? session.started_at : session.starts_at)}</strong></div>
            <div><span className="text-[10px] font-semibold uppercase text-muted-foreground">{inProgress ? "Elapsed" : "Duration"}</span><strong className="mt-1 block text-sm tabular-nums">{inProgress ? elapsedLabel(session.started_at, now) : `${Math.round((new Date(session.ends_at).getTime() - new Date(session.starts_at).getTime()) / 60000)} min`}</strong></div>
            <div><span className="text-[10px] font-semibold uppercase text-muted-foreground">Format</span><strong className="mt-1 block truncate text-sm">{session.appointment_format || "Not set"}</strong></div>
            {session.location_or_link ? <div className="sm:col-span-3"><span className="text-[10px] font-semibold uppercase text-muted-foreground">Room or link</span><strong className="mt-1 block break-all text-sm">{session.location_or_link}</strong></div> : null}
          </section>
          {!inProgress ? (
            <div className={`rounded-xl border p-3 text-sm ${session.is_overdue ? "border-red-400 bg-red-50 text-red-800 dark:bg-red-950/25 dark:text-red-200" : "border-amber-400/50 bg-amber-50 text-amber-900 dark:bg-amber-950/20 dark:text-amber-100"}`}>
              <p className="flex items-center gap-2 font-semibold">{session.is_overdue ? <AlertTriangle className="h-4 w-4" /> : <Clock3 className="h-4 w-4" />}{session.is_overdue ? "Interview is overdue" : startAvailable ? "Interview is ready to start" : "Start is not available yet"}</p>
              {!startAvailable && session.start_available_at ? <p className="mt-1 text-xs">Available {dateTimeLabel(session.start_available_at)}</p> : null}
            </div>
          ) : (
            <label className="text-xs font-semibold">Interview notes<textarea ref={notesRef} autoFocus name="notes" className={`${fieldClass} mt-1 min-h-32`} placeholder="Record the interview observations…" /></label>
          )}
          {confirmFail ? <div role="alert" className="rounded-xl border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"><p className="flex items-center gap-2 font-semibold"><AlertTriangle className="h-4 w-4" />Reject {candidate.full_name}?</p><p className="mt-1 text-xs leading-5">Failing this interview automatically rejects the candidate and cancels remaining appointments.</p></div> : null}
        </ModalBody>
        <ModalFooter>
          {!inProgress ? <div className="flex justify-end gap-2"><button type="button" className={secondaryButtonClass} onClick={onClose}>Close</button><button type="button" className={buttonClass} disabled={!startAvailable || pending} onClick={() => start.mutate()}>{start.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}Start interview</button></div> : confirmFail ? <div className="flex justify-end gap-2"><button type="button" className={secondaryButtonClass} onClick={() => setConfirmFail(false)}>Keep interviewing</button><button type="button" className="inline-flex min-h-9 items-center gap-2 rounded-lg bg-destructive px-3 text-sm font-semibold text-destructive-foreground" disabled={pending} onClick={() => complete.mutate({ result: "failed", notes: notesRef.current?.value || "" })}>{complete.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <XCircle className="h-4 w-4" />}Confirm fail</button></div> : <div className="flex items-center justify-between gap-2"><button type="button" className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-destructive/40 px-3 text-sm font-semibold text-destructive" disabled={pending} onClick={() => setConfirmFail(true)}><XCircle className="h-4 w-4" />Fail</button><button type="submit" className="inline-flex min-h-9 items-center gap-2 rounded-lg bg-emerald-700 px-3 text-sm font-semibold text-white" disabled={pending}>{complete.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}Pass</button></div>}
        </ModalFooter>
      </form>
    </Modal>
  );
}
