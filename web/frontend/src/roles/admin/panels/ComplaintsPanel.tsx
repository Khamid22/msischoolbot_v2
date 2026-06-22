import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  MessageSquare,
  RotateCcw,
  Send,
  ShieldAlert,
} from "lucide-react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { routes } from "@/shared/lib/routes";
import { asNumber, asString } from "../shared";

const statuses = [
  { key: "open", label: "Open" },
  { key: "new", label: "New" },
  { key: "in_progress", label: "In Progress" },
  { key: "escalated", label: "Escalated" },
  { key: "resolved", label: "Resolved" },
];

const categoryLabels: Record<string, string> = {
  complaint: "Complaint",
  direct_contact: "Direct Contact",
  payment: "Payment",
  teacher: "Teacher",
  lesson_quality: "Lesson Quality",
  schedule: "Schedule",
  attendance: "Attendance",
  technical: "Technical",
  account: "Account",
  other: "Complaint",
};

function complaintStatus(value: unknown) {
  const status = asString(value).toLowerCase();
  if (status === "in_progress" || status === "escalated" || status === "resolved") return status;
  return "new";
}

function statusLabel(value: unknown) {
  const status = complaintStatus(value);
  if (status === "in_progress") return "In Progress";
  if (status === "escalated") return "Escalated";
  if (status === "resolved") return "Resolved";
  return "New";
}

function statusClass(value: unknown) {
  const status = complaintStatus(value);
  if (status === "resolved") return "border-emerald-100 bg-emerald-50 text-emerald-700";
  if (status === "escalated") return "border-rose-100 bg-rose-50 text-rose-700";
  if (status === "in_progress") return "border-sky-100 bg-sky-50 text-sky-700";
  return "border-amber-100 bg-amber-50 text-amber-700";
}

function formatDate(value: unknown) {
  const raw = asString(value);
  if (!raw) return "";
  const parsed = Date.parse(raw);
  if (!Number.isFinite(parsed)) return raw;
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(new Date(parsed));
}

function formatDateTime(value: unknown) {
  const raw = asString(value);
  if (!raw) return "";
  const parsed = Date.parse(raw);
  if (!Number.isFinite(parsed)) return raw;
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(parsed));
}

function categoryLabel(value: unknown) {
  const key = asString(value).toLowerCase();
  return categoryLabels[key] || "Complaint";
}

function complaintTitle(complaint: Record<string, unknown>) {
  return asString(complaint.topic) || categoryLabel(complaint.category);
}

function parentLabel(complaint: Record<string, unknown>) {
  return asString(complaint.parent_display) || asString(complaint.parent_login) || "Parent";
}

function metricCount(complaints: Array<Record<string, unknown>>, status: string) {
  return complaints.filter((item) => complaintStatus(item.status) === status).length;
}

function Metric({ label, value, detail, tone }: { label: string; value: number; detail: string; tone: string }) {
  return (
    <div className={`rounded-lg border border-foreground/10 p-3 ${tone}`}>
      <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-2 text-2xl font-bold leading-none">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
    </div>
  );
}

type ThreadMessage = {
  id?: number;
  author_role?: string;
  author_login?: string;
  body?: string;
  created_at?: string;
};

function TicketListItem({
  complaint,
  active,
  onSelect,
}: {
  complaint: Record<string, unknown>;
  active: boolean;
  onSelect: () => void;
}) {
  const replyCount = asNumber(complaint.reply_count);
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-lg border px-3 py-2.5 text-left transition-colors ${
        active ? "border-foreground/25 bg-foreground/6" : "border-foreground/10 bg-background hover:bg-muted"
      }`}
    >
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
        {formatDate(complaint.created_at)}
      </p>
      <p className="mt-1 line-clamp-2 text-xs text-foreground/70">{asString(complaint.message)}</p>
      {replyCount > 0 ? (
        <p className="mt-1 text-[10px] font-semibold text-muted-foreground">
          {replyCount} {replyCount === 1 ? "reply" : "replies"}
        </p>
      ) : null}
    </button>
  );
}

function TicketDetail({
  complaint,
  saving,
  onReply,
  onStatus,
  onOpenParent,
  studentHref,
}: {
  complaint: Record<string, unknown>;
  saving: boolean;
  onReply: (body: string) => Promise<void>;
  onStatus: (status: string) => Promise<void>;
  onOpenParent: () => void;
  studentHref: string;
}) {
  const [reply, setReply] = useState("");
  const status = complaintStatus(complaint.status);
  const messages = Array.isArray(complaint.messages)
    ? (complaint.messages as ThreadMessage[])
    : [];

  useEffect(() => {
    setReply("");
  }, [asNumber(complaint.id)]);

  async function submitReply() {
    const body = reply.trim();
    if (!body || saving) return;
    await onReply(body);
    setReply("");
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header + parent / student summary */}
      <div className="border-b border-foreground/8 pb-3">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-bold">{complaintTitle(complaint)}</h3>
          <span className={`rounded-md border px-2 py-0.5 text-[11px] font-bold ${statusClass(complaint.status)}`}>
            {statusLabel(complaint.status)}
          </span>
          <span className="rounded-md bg-muted px-2 py-0.5 text-[11px] font-bold text-muted-foreground">
            {categoryLabel(complaint.category)}
          </span>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
          <button
            type="button"
            onClick={onOpenParent}
            className="inline-flex items-center gap-1 font-bold text-sky-700 hover:underline"
          >
            {parentLabel(complaint)}
            <ExternalLink className="h-3 w-3" />
          </button>
          {asString(complaint.parent_phone) ? (
            <span className="text-muted-foreground">{asString(complaint.parent_phone)}</span>
          ) : null}
          {asString(complaint.parent_email) ? (
            <span className="text-muted-foreground">{asString(complaint.parent_email)}</span>
          ) : null}
          {asString(complaint.student_name) ? (
            studentHref ? (
              <a href={studentHref} className="font-semibold text-foreground hover:underline">
                {asString(complaint.student_name)}
              </a>
            ) : (
              <span className="text-muted-foreground">{asString(complaint.student_name)}</span>
            )
          ) : null}
          <span className="text-muted-foreground">{formatDateTime(complaint.created_at)}</span>
        </div>
      </div>

      {/* Conversation thread */}
      <div className="min-h-[8rem] flex-1 space-y-3 overflow-y-auto py-3">
        {messages.length ? (
          messages.map((message, index) => {
            const isParent = asString(message.author_role).toLowerCase() === "parent";
            return (
              <div key={`${message.id || 0}-${index}`} className={`flex ${isParent ? "justify-start" : "justify-end"}`}>
                <div
                  className={`max-w-[85%] rounded-lg border px-3 py-2 ${
                    isParent
                      ? "border-foreground/10 bg-background"
                      : "border-sky-100 bg-sky-50"
                  }`}
                >
                  <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                    {isParent ? parentLabel(complaint) : asString(message.author_login) || asString(message.author_role) || "Support"}
                    {" · "}
                    {formatDateTime(message.created_at)}
                  </p>
                  <p className="mt-1 whitespace-pre-wrap text-sm leading-6">{asString(message.body)}</p>
                </div>
              </div>
            );
          })
        ) : (
          <p className="text-sm text-muted-foreground">No messages yet.</p>
        )}
      </div>

      {/* Reply + actions */}
      <div className="border-t border-foreground/8 pt-3">
        <textarea
          value={reply}
          onChange={(event) => setReply(event.target.value)}
          rows={3}
          className="w-full resize-none rounded-lg border border-foreground/10 bg-surface px-3 py-2 text-sm outline-none focus:border-foreground/30"
          placeholder="Write a reply to the parent..."
        />
        <div className="mt-2 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={submitReply}
            disabled={saving || !reply.trim()}
            className="inline-flex h-9 items-center gap-2 rounded-lg bg-primary px-3 text-xs font-bold text-primary-foreground transition-opacity disabled:opacity-40"
          >
            <Send className="h-3.5 w-3.5" />
            Reply
          </button>
          {status !== "escalated" && status !== "resolved" ? (
            <button
              type="button"
              onClick={() => onStatus("escalated")}
              disabled={saving}
              className="inline-flex h-9 items-center gap-2 rounded-lg border border-rose-100 bg-rose-50 px-3 text-xs font-bold text-rose-700 hover:bg-rose-100 disabled:opacity-50"
            >
              <ShieldAlert className="h-3.5 w-3.5" />
              Escalate to CEO
            </button>
          ) : null}
          {status !== "resolved" ? (
            <button
              type="button"
              onClick={() => onStatus("resolved")}
              disabled={saving}
              className="inline-flex h-9 items-center gap-2 rounded-lg border border-emerald-100 bg-emerald-50 px-3 text-xs font-bold text-emerald-700 hover:bg-emerald-100 disabled:opacity-50"
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              Resolve
            </button>
          ) : (
            <button
              type="button"
              onClick={() => onStatus("in_progress")}
              disabled={saving}
              className="inline-flex h-9 items-center gap-2 rounded-lg border border-foreground/10 bg-surface px-3 text-xs font-bold hover:bg-muted disabled:opacity-50"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reopen
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ComplaintsPanel({ state }: { state: any }) {
  const csrf = asString(state.props?.csrfToken);
  const currentSchool = asString(state.currentSchool) || "all";
  const complaints = Array.isArray(state.complaints)
    ? (state.complaints as Array<Record<string, unknown>>)
    : Array.isArray(state.props?.adminComplaints)
      ? (state.props.adminComplaints as Array<Record<string, unknown>>)
      : [];
  const [filter, setFilter] = useState("open");
  const [savingId, setSavingId] = useState(0);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState(0);

  const filteredComplaints = useMemo(() => {
    if (filter === "open") {
      return complaints.filter((item) => complaintStatus(item.status) !== "resolved");
    }
    return complaints.filter((item) => complaintStatus(item.status) === filter);
  }, [complaints, filter]);

  const selectedComplaint =
    complaints.find((item) => asNumber(item.id) === selectedId) || filteredComplaints[0];
  const selectedResolvedId = asNumber(selectedComplaint?.id);

  function replaceComplaint(nextComplaint: Record<string, unknown>) {
    if (typeof state.setComplaints !== "function") return;
    state.setComplaints((current: Array<Record<string, unknown>>) =>
      current.map((item) => (asNumber(item.id) === asNumber(nextComplaint.id) ? nextComplaint : item)),
    );
  }

  function openParent(parentId: number) {
    if (!parentId) return;
    if (typeof state.setActiveParentId === "function") state.setActiveParentId(parentId);
    if (typeof state.switchAdminTab === "function") state.switchAdminTab("parents");
  }

  async function sendUpdate(complaintId: number, url: string, payload: Record<string, unknown>) {
    if (!complaintId || savingId) return;
    setSavingId(complaintId);
    setError("");
    try {
      const response = await fetch(url, {
        method: url.endsWith("/replies") ? "POST" : "PATCH",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf,
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify(payload),
      });
      const json = await response.json().catch(() => ({}));
      if (!response.ok || !json.ok) {
        setError(asString(json.message) || "Unable to update ticket.");
        return;
      }
      if (json.complaint && typeof json.complaint === "object") {
        replaceComplaint(json.complaint as Record<string, unknown>);
      }
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSavingId(0);
    }
  }

  async function replyToTicket(body: string) {
    await sendUpdate(selectedResolvedId, routes.adminComplaintReplies(selectedResolvedId), { body });
  }

  async function changeStatus(status: string) {
    await sendUpdate(selectedResolvedId, routes.adminComplaintApi(selectedResolvedId), { status });
  }

  const studentHref =
    selectedComplaint && asNumber(selectedComplaint.student_row_id) > 0
      ? routes.adminStudentPanel(asNumber(selectedComplaint.student_row_id), currentSchool)
      : "";

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="New" value={metricCount(complaints, "new")} detail="need first reply" tone="bg-amber-50" />
        <Metric label="In Progress" value={metricCount(complaints, "in_progress")} detail="support handling" tone="bg-sky-50" />
        <Metric label="Escalated" value={metricCount(complaints, "escalated")} detail="CEO attention" tone="bg-rose-50" />
        <Metric label="Resolved" value={metricCount(complaints, "resolved")} detail="already answered" tone="bg-emerald-50" />
      </div>

      <ChartCard
        title="Support Tickets"
        subtitle={`${filteredComplaints.length} shown`}
        icon={<MessageSquare className="h-4 w-4 text-info" />}
      >
        <div className="space-y-3">
          {error ? (
            <div className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm font-semibold text-destructive">
              {error}
            </div>
          ) : null}

          <div className="flex flex-wrap gap-2">
            {statuses.map((status) => (
              <button
                key={status.key}
                type="button"
                onClick={() => setFilter(status.key)}
                className={`h-8 rounded-lg border px-3 text-xs font-bold transition-colors ${
                  filter === status.key
                    ? "border-foreground bg-foreground text-background"
                    : "border-foreground/10 bg-surface hover:bg-muted"
                }`}
              >
                {status.label}
              </button>
            ))}
          </div>

          {complaints.length ? (
            <div className="grid gap-3 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
              {/* Ticket queue */}
              <div className="max-h-[68dvh] space-y-2 overflow-y-auto pr-1">
                {filteredComplaints.length ? (
                  filteredComplaints.map((complaint) => (
                    <TicketListItem
                      key={asNumber(complaint.id)}
                      complaint={complaint}
                      active={asNumber(complaint.id) === selectedResolvedId}
                      onSelect={() => setSelectedId(asNumber(complaint.id))}
                    />
                  ))
                ) : (
                  <p className="py-6 text-center text-sm text-muted-foreground">No tickets in this queue.</p>
                )}
              </div>

              {/* Ticket detail / thread */}
              <div className="rounded-lg border border-foreground/10 bg-background p-4">
                {selectedComplaint ? (
                  <TicketDetail
                    complaint={selectedComplaint}
                    saving={savingId === selectedResolvedId}
                    onReply={replyToTicket}
                    onStatus={changeStatus}
                    onOpenParent={() => openParent(asNumber(selectedComplaint.parent_admin_id))}
                    studentHref={studentHref}
                  />
                ) : (
                  <p className="py-10 text-center text-sm text-muted-foreground">
                    Select a ticket to view the conversation.
                  </p>
                )}
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-10 text-center">
              <AlertCircle className="mx-auto h-5 w-5 text-muted-foreground" />
              <p className="mt-2 text-sm font-bold">No support tickets yet.</p>
            </div>
          )}
        </div>
      </ChartCard>
    </div>
  );
}
