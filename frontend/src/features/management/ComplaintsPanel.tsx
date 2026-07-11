import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  PlayCircle,
  RotateCcw,
  Search,
  Send,
  ShieldAlert,
} from "lucide-react";
import { routes } from "@/shared/lib/routes";
import { asNumber, asString } from "@/features/managementTypes";
import {
  complaintStatus,
  complaintTitle,
  formatDate,
  formatDateTime,
  lastUpdated,
  matchesQuery,
  parentLabel,
  statusClass,
  statusLabel,
  type ThreadMessage,
} from "./complaintFormat";
import { apiData, apiErrorMessage, apiSucceeded, jsonCsrfHeaders } from "@/shared/lib/api";

// Filter options for the helpdesk queue. "all" / "open" are virtual: "open"
// keeps every ticket that still needs work (anything not resolved), the rest map
// 1:1 to a stored status. Status keys stay in sync with the backend
// (new / in_progress / escalated / resolved).
const filterOptions = [
  { key: "all", label: "All" },
  { key: "open", label: "Open" },
  { key: "in_progress", label: "In Progress" },
  { key: "escalated", label: "Escalated" },
  { key: "resolved", label: "Resolved" },
];

function TicketListItem({
  complaint,
  active,
  onSelect,
}: {
  complaint: Record<string, unknown>;
  active: boolean;
  onSelect: () => void;
}) {
  const assigned = asString(complaint.assigned_to);
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-lg border px-3 py-2.5 text-left transition-colors ${
        active ? "border-foreground/25 bg-white shadow-sm" : "border-foreground/10 bg-white hover:bg-muted/60"
      }`}
    >
      <div className="flex items-center gap-2">
        <span className="min-w-0 flex-1 truncate text-sm font-bold">{parentLabel(complaint)}</span>
        <span className={`shrink-0 rounded-md border px-1.5 py-0.5 text-[10px] font-bold ${statusClass(complaint.status)}`}>
          {statusLabel(complaint.status)}
        </span>
      </div>
      <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
        {asString(complaint.student_name) || "No student linked"}
        {" · "}
        {complaintTitle(complaint)}
      </p>
      <p className="mt-1 line-clamp-1 text-xs text-foreground/70">{asString(complaint.message)}</p>
      <div className="mt-1.5 flex items-center justify-between gap-2">
        <span className="truncate text-[10px] text-muted-foreground">
          {formatDate(lastUpdated(complaint))}
          {assigned ? ` · ${assigned}` : ""}
        </span>
        <span className="shrink-0 rounded-md border border-foreground/10 px-2 py-0.5 text-[10px] font-bold text-foreground/70">
          Open
        </span>
      </div>
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
    <div className="flex h-full min-h-0 flex-col">
      {/* Header + parent / student identity */}
      <div className="border-b border-foreground/8 pb-3">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-bold">{complaintTitle(complaint)}</h3>
          <span className={`rounded-md border px-2 py-0.5 text-[11px] font-bold ${statusClass(complaint.status)}`}>
            {statusLabel(complaint.status)}
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
          <span className="text-muted-foreground">·</span>
          {asString(complaint.student_name) ? (
            studentHref ? (
              <a href={studentHref} className="font-semibold text-foreground hover:underline">
                {asString(complaint.student_name)}
              </a>
            ) : (
              <span className="font-semibold text-foreground">{asString(complaint.student_name)}</span>
            )
          ) : (
            <span className="text-muted-foreground">No student linked</span>
          )}
          {asString(complaint.assigned_to) ? (
            <span className="text-muted-foreground">Assigned: {asString(complaint.assigned_to)}</span>
          ) : null}
        </div>
      </div>

      {/* Conversation thread */}
      <div className="min-h-[14rem] flex-1 space-y-3 overflow-y-auto py-3 lg:min-h-0">
        {messages.length ? (
          messages.map((message, index) => {
            const isParent = asString(message.author_role).toLowerCase() === "parent";
            return (
              <div key={`${message.id || 0}-${index}`} className={`flex ${isParent ? "justify-start" : "justify-end"}`}>
                <div
                  className={`max-w-[92%] rounded-lg border px-3 py-2 sm:max-w-[85%] ${
                    isParent
                      ? "border-foreground/10 bg-white"
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
      <div className="shrink-0 border-t border-foreground/8 pt-3">
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
          {status !== "in_progress" && status !== "resolved" ? (
            <button
              type="button"
              onClick={() => onStatus("in_progress")}
              disabled={saving}
              className="inline-flex h-9 items-center gap-2 rounded-lg border border-sky-100 bg-sky-50 px-3 text-xs font-bold text-sky-700 hover:bg-sky-100 disabled:opacity-50"
            >
              <PlayCircle className="h-3.5 w-3.5" />
              Mark In Progress
            </button>
          ) : null}
          {status !== "escalated" && status !== "resolved" ? (
            <button
              type="button"
              onClick={() => onStatus("escalated")}
              disabled={saving}
              className="inline-flex h-9 items-center gap-2 rounded-lg border border-rose-100 bg-rose-50 px-3 text-xs font-bold text-rose-700 hover:bg-rose-100 disabled:opacity-50"
            >
              <ShieldAlert className="h-3.5 w-3.5" />
              Escalate
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
  const [query, setQuery] = useState("");
  const [savingId, setSavingId] = useState(0);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState(0);

  const filteredComplaints = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return complaints.filter((item) => {
      if (!matchesQuery(item, needle)) return false;
      if (filter === "all") return true;
      if (filter === "open") return complaintStatus(item.status) !== "resolved";
      return complaintStatus(item.status) === filter;
    });
  }, [complaints, filter, query]);

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
        headers: jsonCsrfHeaders(csrf),
        body: JSON.stringify(payload),
      });
      const json = await response.json().catch(() => ({}));
      if (!apiSucceeded(response, json)) {
        setError(apiErrorMessage(json, "Unable to update ticket."));
        return;
      }
      const complaint = apiData<{ complaint?: unknown }>(json).complaint;
      if (complaint && typeof complaint === "object") {
        replaceComplaint(complaint as Record<string, unknown>);
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

  if (!complaints.length) {
    return (
      <div className="rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-12 text-center">
        <AlertCircle className="mx-auto h-5 w-5 text-muted-foreground" />
        <p className="mt-2 text-sm font-bold">No support tickets yet.</p>
        <p className="mt-1 text-xs text-muted-foreground">Parent complaints and questions will appear here.</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-[calc(var(--tg-app-height)-var(--app-top-inset)-var(--app-bottom-inset)-6rem)] flex-col gap-3 lg:min-h-[calc(var(--tg-app-height)-2rem)]">
      {error ? (
        <div className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm font-semibold text-destructive">
          {error}
        </div>
      ) : null}

      {/* Top bar: search + status filter */}
      <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_12rem]">
        <div className="relative min-w-0 flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search tickets by parent, student, or message"
            className="h-9 w-full rounded-lg border border-foreground/10 bg-surface pl-9 pr-3 text-sm outline-none focus:border-foreground/30"
          />
        </div>
        <select
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          aria-label="Filter tickets by status"
          className="h-9 w-full rounded-lg border border-foreground/10 bg-surface px-3 text-sm font-semibold outline-none focus:border-foreground/30"
        >
          {filterOptions.map((option) => (
            <option key={option.key} value={option.key}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {/* Queue (left) + conversation (right) */}
      <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-[minmax(18rem,0.8fr)_minmax(0,1.2fr)]">
        <div className="min-h-[14rem] max-h-[38dvh] space-y-2 overflow-y-auto pr-1 lg:max-h-none lg:min-h-0">
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
            <p className="py-6 text-center text-sm text-muted-foreground">No tickets match this view.</p>
          )}
        </div>

        <div className="min-h-[24rem] min-w-0 rounded-lg border border-foreground/10 bg-white p-4 shadow-sm lg:min-h-0">
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
    </div>
  );
}
