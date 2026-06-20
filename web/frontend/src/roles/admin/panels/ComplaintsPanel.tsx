import { useMemo, useState } from "react";
import { AlertCircle, CheckCircle2, MessageSquare, Send, ShieldAlert } from "lucide-react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { routes } from "@/shared/lib/routes";
import { asNumber, asString } from "../shared";

const statuses = [
  { key: "open", label: "Open" },
  { key: "new", label: "New" },
  { key: "direct_contact", label: "Direct Contact" },
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
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
  }).format(new Date(parsed));
}

function categoryLabel(value: unknown) {
  const key = asString(value).toLowerCase();
  return categoryLabels[key] || "Complaint";
}

function complaintTitle(complaint: Record<string, unknown>) {
  return asString(complaint.topic) || categoryLabel(complaint.category);
}

function metricCount(complaints: Array<Record<string, unknown>>, status: string) {
  return complaints.filter((item) => complaintStatus(item.status) === status).length;
}

function Metric({
  label,
  value,
  detail,
  tone,
}: {
  label: string;
  value: number;
  detail: string;
  tone: string;
}) {
  return (
    <div className={`rounded-lg border border-foreground/10 p-3 ${tone}`}>
      <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-2 text-2xl font-bold leading-none">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
    </div>
  );
}

function ComplaintCard({
  complaint,
  savingId,
  onUpdate,
}: {
  complaint: Record<string, unknown>;
  savingId: number;
  onUpdate: (complaintId: number, payload: Record<string, unknown>) => Promise<void>;
}) {
  const complaintId = asNumber(complaint.id);
  const [reply, setReply] = useState(asString(complaint.reply));
  const saving = savingId === complaintId;
  const title = complaintTitle(complaint);

  async function send(status: string) {
    await onUpdate(complaintId, { status, reply });
  }

  return (
    <article className="rounded-lg border border-foreground/10 bg-background p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-bold">{title}</h3>
            <span className={`rounded-md border px-2 py-1 text-[11px] font-bold ${statusClass(complaint.status)}`}>
              {statusLabel(complaint.status)}
            </span>
            <span className="rounded-md bg-muted px-2 py-1 text-[11px] font-bold text-muted-foreground">
              {categoryLabel(complaint.category)}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {asString(complaint.parent_login) || "Parent"} · {asString(complaint.student_name) || "Student"} · {formatDate(complaint.created_at)}
          </p>
        </div>
      </div>

      <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-foreground/85">
        {asString(complaint.message)}
      </p>

      <label className="mt-4 block">
        <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
          Reply
        </span>
        <textarea
          value={reply}
          onChange={(event) => setReply(event.target.value)}
          rows={3}
          className="w-full resize-none rounded-lg border border-foreground/10 bg-surface px-3 py-2 text-sm outline-none focus:border-foreground/30"
          placeholder="Write a short answer for the parent..."
        />
      </label>

      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => send("in_progress")}
          disabled={saving}
          className="inline-flex h-9 items-center gap-2 rounded-lg border border-foreground/10 bg-surface px-3 text-xs font-bold hover:bg-muted disabled:opacity-50"
        >
          <Send className="h-3.5 w-3.5" />
          Reply
        </button>
        <button
          type="button"
          onClick={() => send("escalated")}
          disabled={saving}
          className="inline-flex h-9 items-center gap-2 rounded-lg border border-rose-100 bg-rose-50 px-3 text-xs font-bold text-rose-700 hover:bg-rose-100 disabled:opacity-50"
        >
          <ShieldAlert className="h-3.5 w-3.5" />
          Escalate to CEO
        </button>
        <button
          type="button"
          onClick={() => send("resolved")}
          disabled={saving}
          className="inline-flex h-9 items-center gap-2 rounded-lg border border-emerald-100 bg-emerald-50 px-3 text-xs font-bold text-emerald-700 hover:bg-emerald-100 disabled:opacity-50"
        >
          <CheckCircle2 className="h-3.5 w-3.5" />
          Resolve
        </button>
      </div>
    </article>
  );
}

export default function ComplaintsPanel({ state }: { state: any }) {
  const csrf = asString(state.props?.csrfToken);
  const complaints = Array.isArray(state.complaints)
    ? (state.complaints as Array<Record<string, unknown>>)
    : Array.isArray(state.props?.adminComplaints)
      ? (state.props.adminComplaints as Array<Record<string, unknown>>)
      : [];
  const [filter, setFilter] = useState("open");
  const [savingId, setSavingId] = useState(0);
  const [error, setError] = useState("");

  const filteredComplaints = useMemo(() => {
    if (filter === "open") {
      return complaints.filter((item) => complaintStatus(item.status) !== "resolved");
    }
    if (filter === "direct_contact") {
      return complaints.filter((item) => asString(item.category).toLowerCase() === "direct_contact" && complaintStatus(item.status) !== "resolved");
    }
    return complaints.filter((item) => complaintStatus(item.status) === filter);
  }, [complaints, filter]);

  function replaceComplaint(nextComplaint: Record<string, unknown>) {
    if (typeof state.setComplaints !== "function") return;
    state.setComplaints((current: Array<Record<string, unknown>>) =>
      current.map((item) => (asNumber(item.id) === asNumber(nextComplaint.id) ? nextComplaint : item)),
    );
  }

  async function updateComplaint(complaintId: number, payload: Record<string, unknown>) {
    if (!complaintId || savingId) return;
    setSavingId(complaintId);
    setError("");
    try {
      const response = await fetch(routes.adminComplaintApi(complaintId), {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf,
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify(payload),
      });
      const json = await response.json().catch(() => ({}));
      if (!response.ok || !json.ok) {
        setError(asString(json.message) || "Unable to update complaint.");
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

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="New" value={metricCount(complaints, "new")} detail="need first reply" tone="bg-amber-50" />
        <Metric label="In Progress" value={metricCount(complaints, "in_progress")} detail="support handling" tone="bg-sky-50" />
        <Metric label="Escalated" value={metricCount(complaints, "escalated")} detail="CEO attention" tone="bg-rose-50" />
        <Metric label="Resolved" value={metricCount(complaints, "resolved")} detail="already answered" tone="bg-emerald-50" />
      </div>

      <ChartCard title="Complaint Queue" subtitle={`${filteredComplaints.length} shown`} icon={<MessageSquare className="h-4 w-4 text-info" />}>
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

          {filteredComplaints.length ? (
            <div className="space-y-3">
              {filteredComplaints.map((complaint) => (
                <ComplaintCard
                  key={asNumber(complaint.id)}
                  complaint={complaint}
                  savingId={savingId}
                  onUpdate={updateComplaint}
                />
              ))}
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-10 text-center">
              <AlertCircle className="mx-auto h-5 w-5 text-muted-foreground" />
              <p className="mt-2 text-sm font-bold">No complaints in this queue.</p>
            </div>
          )}
        </div>
      </ChartCard>
    </div>
  );
}
