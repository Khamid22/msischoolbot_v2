import { useEffect, useRef, useState } from "react";
import { Globe, Layers, Loader2, MessageSquare, Pencil, Send, Trash2, Users, X } from "lucide-react";
import { AdminEmbedLayout, isAdminEmbedMode } from "@/shared/ui/AdminEmbedLayout";
import { TelegramLayout, Topbar } from "@/shared/ui/TelegramLayout";

interface ChatMessage {
  id: number;
  room: string;
  authorName: string;
  authorStudentId: string;
  body: string;
  editedAt: string | null;
  createdAt: string;
  createdAtRaw: string;
}

interface ChatPageProps {
  backUrl?: string;
  currentStudent?: {
    fullName?: string;
    studentLogin?: string;
    subject?: string;
    group?: string;
  };
  availableRooms?: Array<{ key: string; label: string; icon: string }>;
  embedMode?: string;
}

const ROOM_ICONS: Record<string, typeof Globe> = {
  globe: Globe,
  layers: Layers,
  users: Users,
};

function RoomIcon({ icon, className }: { icon: string; className?: string }) {
  const Icon = ROOM_ICONS[icon] ?? MessageSquare;
  return <Icon className={className} />;
}

function MessageBubble({
  msg,
  isOwn,
  onEdit,
  onDelete,
}: {
  msg: ChatMessage;
  isOwn: boolean;
  onEdit: (msg: ChatMessage) => void;
  onDelete: (id: number) => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className={`flex w-full gap-2 ${isOwn ? "flex-row-reverse" : "flex-row"}`}>
      <div className="flex h-7 w-7 shrink-0 items-center justify-center self-end rounded-full bg-muted text-[10px] font-bold uppercase text-muted-foreground">
        {msg.authorName.charAt(0)}
      </div>
      <div className={`group relative max-w-[75%] ${isOwn ? "items-end" : "items-start"} flex flex-col`}>
        {!isOwn && (
          <span className="mb-0.5 text-[10px] font-semibold text-muted-foreground">{msg.authorName}</span>
        )}
        <div
          className={`relative rounded-2xl px-3 py-2 text-xs leading-relaxed ${
            isOwn
              ? "rounded-br-sm bg-foreground text-background"
              : "rounded-bl-sm bg-surface border border-foreground/8 text-foreground"
          }`}
        >
          {msg.body}
          {msg.editedAt && (
            <span className="ml-1.5 text-[9px] opacity-50">(edited)</span>
          )}
        </div>
        <span className="mt-0.5 text-[9px] text-muted-foreground">{msg.createdAt}</span>
        {isOwn && (
          <div className="absolute -top-1 right-0 hidden items-center gap-1 group-hover:flex">
            <button
              type="button"
              onClick={() => onEdit(msg)}
              className="flex h-6 w-6 items-center justify-center rounded-full bg-surface shadow-card hover:bg-muted"
              aria-label="Edit"
            >
              <Pencil className="h-3 w-3" />
            </button>
            <button
              type="button"
              onClick={() => onDelete(msg.id)}
              className="flex h-6 w-6 items-center justify-center rounded-full bg-surface text-destructive shadow-card hover:bg-muted"
              aria-label="Delete"
            >
              <Trash2 className="h-3 w-3" />
            </button>
          </div>
        )}
      </div>
      {menuOpen && <span className="hidden" onClick={() => setMenuOpen(false)} />}
    </div>
  );
}

export default function ChatPage(props: ChatPageProps) {
  const currentLogin = props.currentStudent?.studentLogin ?? "";
  const defaultRooms: Array<{ key: string; label: string; icon: string }> = [
    { key: "global", label: "Global", icon: "globe" },
    ...(props.currentStudent?.subject
      ? [{ key: `subject:${props.currentStudent.subject}`, label: props.currentStudent.subject, icon: "layers" }]
      : []),
    ...(props.currentStudent?.group
      ? [{ key: `group:${props.currentStudent.group}`, label: props.currentStudent.group, icon: "users" }]
      : []),
  ];
  const rooms = Array.isArray(props.availableRooms) && props.availableRooms.length
    ? props.availableRooms
    : defaultRooms;

  const [activeRoom, setActiveRoom] = useState(rooms[0]?.key ?? "global");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState("");
  const [editTarget, setEditTarget] = useState<ChatMessage | null>(null);
  const [editBody, setEditBody] = useState("");
  const [saving, setSaving] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const latestIdRef = useRef(0);
  async function fetchMessages(room: string) {
    setLoading(true);
    setMessages([]);
    latestIdRef.current = 0;
    try {
      const res = await fetch(`/api/chat/messages?room=${encodeURIComponent(room)}`);
      const data = await res.json();
      const msgs: ChatMessage[] = Array.isArray(data.messages) ? data.messages : [];
      setMessages(msgs);
      setHasMore(msgs.length >= 40);
      if (msgs.length) latestIdRef.current = msgs[msgs.length - 1].id;
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "instant" }), 30);
    } catch {
    } finally {
      setLoading(false);
    }
  }
  async function pollNew(room: string) {
    if (!latestIdRef.current) return;
    if (typeof document !== "undefined" && document.visibilityState === "hidden") {
      return;
    }
    try {
      const res = await fetch(
        `/api/chat/messages?room=${encodeURIComponent(room)}&after_id=${latestIdRef.current}`
      );
      const data = await res.json();
      const incoming: ChatMessage[] = Array.isArray(data.messages) ? data.messages : [];
      if (incoming.length) {
        setMessages((prev) => {
          // merge, avoid duplicates
          const known = new Set(prev.map((m) => m.id));
          const toAdd = incoming.filter((m) => !known.has(m.id));
          return toAdd.length ? [...prev, ...toAdd] : prev;
        });
        latestIdRef.current = Math.max(...incoming.map((m) => m.id));
        setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
      }
    } catch {
    }
  }
  async function loadMore() {
    const oldest = messages[0]?.id ?? 0;
    if (!oldest) return;
    try {
      const res = await fetch(
        `/api/chat/messages?room=${encodeURIComponent(activeRoom)}&before_id=${oldest}`
      );
      const data = await res.json();
      const older: ChatMessage[] = Array.isArray(data.messages) ? data.messages : [];
      if (older.length) {
        setMessages((prev) => [...older, ...prev]);
        setHasMore(older.length >= 40);
      } else {
        setHasMore(false);
      }
    } catch {
    }
  }

  useEffect(() => {
    fetchMessages(activeRoom);
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(() => pollNew(activeRoom), 7000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [activeRoom]);
  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const body = draft.trim();
    if (!body || sending) return;
    setSending(true);
    setSendError("");
    try {
      const res = await fetch("/api/chat/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ room: activeRoom, body }),
      });
      const data = await res.json();
      if (!res.ok) {
        setSendError(data.error ?? "Failed to send.");
      } else {
        setDraft("");
        setMessages((prev) => {
          const known = new Set(prev.map((m) => m.id));
          if (known.has(data.message.id)) return prev;
          return [...prev, data.message];
        });
        latestIdRef.current = Math.max(latestIdRef.current, data.message.id);
        setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
      }
    } catch {
      setSendError("Network error.");
    } finally {
      setSending(false);
    }
  }
  async function handleDelete(id: number) {
    const res = await fetch(`/api/chat/messages/${id}`, { method: "DELETE" });
    if (res.ok) setMessages((prev) => prev.filter((m) => m.id !== id));
  }
  function startEdit(msg: ChatMessage) {
    setEditTarget(msg);
    setEditBody(msg.body);
  }

  async function saveEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!editTarget || saving) return;
    const body = editBody.trim();
    if (!body) return;
    setSaving(true);
    try {
      const res = await fetch(`/api/chat/messages/${editTarget.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body }),
      });
      const data = await res.json();
      if (res.ok) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === editTarget.id ? { ...m, body: data.body, editedAt: data.editedAt } : m
          )
        );
        setEditTarget(null);
        setEditBody("");
      }
    } finally {
      setSaving(false);
    }
  }

  const activeRoomLabel = rooms.find((r) => r.key === activeRoom)?.label ?? activeRoom;
  const isAdminEmbed = isAdminEmbedMode(props.embedMode);
  const pageContent = (
    <>
      <div className={`flex flex-col animate-in ${isAdminEmbed ? "h-[calc(100dvh-8rem)] min-h-[34rem]" : "h-full"}`}>
        <div className="mb-3 flex gap-2 overflow-x-auto pb-0.5">
          {rooms.map((room) => (
            <button
              key={room.key}
              type="button"
              onClick={() => setActiveRoom(room.key)}
              className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                activeRoom === room.key
                  ? "bg-foreground text-background"
                  : "bg-surface border border-foreground/10 text-foreground hover:bg-muted"
              }`}
            >
              <RoomIcon icon={room.icon} className="h-3 w-3" />
              {room.label}
            </button>
          ))}
        </div>
        <div className="mb-3 flex min-h-0 flex-1 flex-col overflow-y-auto rounded-2xl border border-foreground/10 bg-surface shadow-card">
          {hasMore && !loading && (
            <div className="flex justify-center py-2">
              <button
                type="button"
                onClick={loadMore}
                className="rounded-full bg-muted px-4 py-1.5 text-[10px] font-semibold text-muted-foreground hover:bg-foreground/10"
              >
                Load earlier messages
              </button>
            </div>
          )}

          {loading ? (
            <div className="flex flex-1 items-center justify-center gap-2 py-8 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-xs">Loading…</span>
            </div>
          ) : messages.length === 0 ? (
            <div className="flex flex-1 items-center justify-center py-12">
              <div className="text-center">
                <MessageSquare className="mx-auto mb-2 h-8 w-8 text-muted-foreground/30" />
                <p className="text-sm font-medium text-muted-foreground">No messages yet</p>
                <p className="text-xs text-muted-foreground/60">Be the first to write something!</p>
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-3 p-4">
              {messages.map((msg) => (
                <MessageBubble
                  key={msg.id}
                  msg={msg}
                  isOwn={msg.authorStudentId.toLowerCase() === currentLogin.toLowerCase()}
                  onEdit={startEdit}
                  onDelete={handleDelete}
                />
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </div>
        <div className="rounded-2xl border border-foreground/10 bg-surface shadow-card">
          <form onSubmit={handleSend} className="flex items-end gap-2 p-3">
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend(e as unknown as React.FormEvent);
                }
              }}
              placeholder={`Message ${activeRoomLabel}…`}
              rows={1}
              maxLength={800}
              className="min-h-[2.25rem] flex-1 resize-none rounded-xl border border-foreground/10 bg-muted px-3 py-2 text-xs outline-none placeholder:text-muted-foreground focus:border-foreground/30"
              style={{ fieldSizing: "content" } as React.CSSProperties}
            />
            <button
              type="submit"
              disabled={!draft.trim() || sending}
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-foreground text-background disabled:opacity-40"
            >
              {sending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
            </button>
          </form>
          {sendError && <p className="px-3 pb-2 text-[10px] text-destructive">{sendError}</p>}
        </div>
      </div>
      {editTarget && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-foreground/60 sm:items-center sm:p-4"
          onClick={() => setEditTarget(null)}
        >
          <div
            className="w-full max-w-lg overflow-hidden rounded-t-2xl bg-surface p-4 shadow-card-hover sm:rounded-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-3 flex items-center justify-between">
              <p className="text-sm font-bold">Edit message</p>
              <button
                type="button"
                onClick={() => setEditTarget(null)}
                className="flex h-7 w-7 items-center justify-center rounded-lg hover:bg-muted"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <form onSubmit={saveEdit} className="flex flex-col gap-3">
              <textarea
                value={editBody}
                onChange={(e) => setEditBody(e.target.value)}
                rows={3}
                maxLength={800}
                className="w-full resize-none rounded-xl border border-foreground/10 bg-muted px-3 py-2 text-xs outline-none focus:border-foreground/30"
                autoFocus
              />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setEditTarget(null)}
                  className="rounded-lg border border-foreground/10 px-4 py-2 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!editBody.trim() || saving}
                  className="rounded-lg bg-foreground px-4 py-2 text-xs font-semibold text-background disabled:opacity-40"
                >
                  {saving ? "Saving…" : "Save"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );

  if (isAdminEmbed) {
    return (
      <AdminEmbedLayout
        title="Chat Room"
        subtitle={activeRoomLabel}
        backUrl={props.backUrl}
        badge={props.currentStudent?.group || "Chat"}
      >
        {pageContent}
      </AdminEmbedLayout>
    );
  }

  return (
    <TelegramLayout
      topbar={
        <Topbar
          backUrl={props.backUrl}
          title="Chat Room"
          subtitle={activeRoomLabel}
          titleIcon={<MessageSquare className="h-4 w-4" />}
        />
      }
    >
      {pageContent}
    </TelegramLayout>
  );
}
