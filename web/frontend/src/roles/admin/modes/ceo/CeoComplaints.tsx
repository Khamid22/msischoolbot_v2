import { useMemo, useState } from "react";
import { AlertCircle, ShieldAlert } from "lucide-react";
import { asNumber, asString } from "@/roles/admin/shared";
import {
  complaintStatus,
  complaintTitle,
  formatDate,
  formatDateTime,
  lastUpdated,
  parentLabel,
  statusClass,
  statusLabel,
  type ThreadMessage,
} from "@/roles/admin/panels/complaintFormat";

// CEO complaints view — a calm, read-only summary. The CEO does not work the
// support queue (reply / triage); they only need the headline numbers plus the
// escalated and resolved tickets. The full operational helpdesk stays in
// ComplaintsPanel for Customer Support / Admin.

function Metric({ label, value, detail, tone }: { label: string; value: number; detail: string; tone: string }) {
  return (
    <div className={`rounded-lg border border-foreground/10 p-3 ${tone}`}>
      <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-2 text-2xl font-bold leading-none">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
    </div>
  );
}

function count(complaints: Array<Record<string, unknown>>, status: string) {
  return complaints.filter((item) => complaintStatus(item.status) === status).length;
}

function ReadOnlyTicket({
  complaint,
  expanded,
  onToggle,
}: {
  complaint: Record<string, unknown>;
  expanded: boolean;
  onToggle: () => void;
}) {
  const messages = Array.isArray(complaint.messages) ? (complaint.messages as ThreadMessage[]) : [];
  const assigned = asString(complaint.assigned_to);
  return (
    <div className="rounded-lg border border-foreground/10 bg-background">
      <button type="button" onClick={onToggle} className="w-full px-3 py-2.5 text-left">
        <div className="flex items-center gap-2">
          <span className="min-w-0 flex-1 truncate text-sm font-bold">{complaintTitle(complaint)}</span>
          <span className={`shrink-0 rounded-md border px-1.5 py-0.5 text-[10px] font-bold ${statusClass(complaint.status)}`}>
            {statusLabel(complaint.status)}
          </span>
        </div>
        <p className="mt-1 truncate text-[11px] text-muted-foreground">
          {parentLabel(complaint)}
          {asString(complaint.student_name) ? ` · ${asString(complaint.student_name)}` : ""}
          {" · "}
          {formatDate(lastUpdated(complaint))}
          {assigned ? ` · ${assigned}` : ""}
        </p>
      </button>
      {expanded ? (
        <div className="space-y-2 border-t border-foreground/8 px-3 py-3">
          {messages.length ? (
            messages.map((message, index) => (
              <div key={`${message.id || 0}-${index}`} className="rounded-lg border border-foreground/10 bg-surface px-3 py-2">
                <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                  {asString(message.author_role).toLowerCase() === "parent"
                    ? parentLabel(complaint)
                    : asString(message.author_login) || asString(message.author_role) || "Support"}
                  {" · "}
                  {formatDateTime(message.created_at)}
                </p>
                <p className="mt-1 whitespace-pre-wrap text-sm leading-6">{asString(message.body)}</p>
              </div>
            ))
          ) : (
            <p className="text-sm text-muted-foreground">{asString(complaint.message) || "No messages yet."}</p>
          )}
        </div>
      ) : null}
    </div>
  );
}

export default function CeoComplaints({ state }: { state: any }) {
  const complaints = Array.isArray(state.complaints)
    ? (state.complaints as Array<Record<string, unknown>>)
    : Array.isArray(state.props?.adminComplaints)
      ? (state.props.adminComplaints as Array<Record<string, unknown>>)
      : [];
  const [expandedId, setExpandedId] = useState(0);

  const escalated = useMemo(
    () => complaints.filter((item) => complaintStatus(item.status) === "escalated"),
    [complaints],
  );
  const resolved = useMemo(
    () => complaints.filter((item) => complaintStatus(item.status) === "resolved"),
    [complaints],
  );

  const openCount = complaints.filter((item) => complaintStatus(item.status) !== "resolved").length;

  function toggle(id: number) {
    setExpandedId((current) => (current === id ? 0 : id));
  }

  if (!complaints.length) {
    return (
      <div className="rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-12 text-center">
        <AlertCircle className="mx-auto h-5 w-5 text-muted-foreground" />
        <p className="mt-2 text-sm font-bold">No complaints on record.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <Metric label="Open" value={openCount} detail="being handled by support" tone="bg-amber-50" />
        <Metric label="Escalated" value={escalated.length} detail="need your attention" tone="bg-rose-50" />
        <Metric label="Resolved" value={resolved.length} detail="closed by support" tone="bg-emerald-50" />
      </div>

      <section className="space-y-2">
        <h3 className="flex items-center gap-1.5 text-sm font-bold">
          <ShieldAlert className="h-4 w-4 text-rose-600" />
          Escalated to you
        </h3>
        {escalated.length ? (
          escalated.map((complaint) => (
            <ReadOnlyTicket
              key={asNumber(complaint.id)}
              complaint={complaint}
              expanded={expandedId === asNumber(complaint.id)}
              onToggle={() => toggle(asNumber(complaint.id))}
            />
          ))
        ) : (
          <p className="rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-6 text-center text-sm text-muted-foreground">
            Nothing escalated right now.
          </p>
        )}
      </section>

      {resolved.length ? (
        <section className="space-y-2">
          <h3 className="text-sm font-bold">Recently resolved</h3>
          {resolved.slice(0, 10).map((complaint) => (
            <ReadOnlyTicket
              key={asNumber(complaint.id)}
              complaint={complaint}
              expanded={expandedId === asNumber(complaint.id)}
              onToggle={() => toggle(asNumber(complaint.id))}
            />
          ))}
        </section>
      ) : null}
    </div>
  );
}
