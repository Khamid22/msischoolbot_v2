import { AlertCircle, AlertTriangle, Search } from "lucide-react";
import { ChartCard } from "@/components/ChartCard";

export default function ChatPanel({ state }: { state: any }) {
  const {
    chatRooms,
    chatRoom,
    setChatRoom,
    loadChatMessages,
    chatLoading,
    chatMessages,
    adminDeleteMsg,
    adminBlockUser,
    blockReason,
    setBlockReason,
    blockedUsers,
    adminUnblock,
  } = state;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {chatRooms.length === 0 && (
          <button type="button" className="inline-flex items-center gap-1.5 rounded-full bg-foreground px-3 py-1.5 text-xs font-semibold text-background">
            Global
          </button>
        )}
        {chatRooms.map((r: { room: string; active: number }) => (
          <button
            key={r.room}
            type="button"
            onClick={() => {
              setChatRoom(r.room);
              loadChatMessages(r.room);
            }}
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
              chatRoom === r.room
                ? "bg-foreground text-background"
                : "bg-muted text-foreground hover:bg-foreground/10"
            }`}
          >
            {r.room} {r.active > 0 && <span className="opacity-60">({r.active})</span>}
          </button>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <ChartCard title={`Messages — ${chatRoom}`} icon={<Search className="h-4 w-4 text-info" />}>
          {chatLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : chatMessages.length === 0 ? (
            <p className="text-sm text-muted-foreground">No messages in this room.</p>
          ) : (
            <div className="space-y-2">
              {chatMessages.map((msg: any) => (
                <div key={msg.id} className={`flex items-start gap-3 rounded-xl border px-3 py-2.5 ${msg.isDeleted ? "border-foreground/5 opacity-40" : "border-foreground/8"}`}>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-baseline gap-1.5">
                      <span className="text-[11px] font-bold">{msg.authorName}</span>
                      <span className="text-[10px] text-muted-foreground">{msg.authorStudentId}</span>
                      <span className="text-[10px] text-muted-foreground">· {msg.createdAt}</span>
                      {msg.isDeleted && <span className="text-[10px] text-destructive">[deleted]</span>}
                      {msg.editedAt && <span className="text-[10px] text-muted-foreground">(edited)</span>}
                    </div>
                    <p className="mt-0.5 text-xs leading-relaxed">{msg.body}</p>
                  </div>
                  {!msg.isDeleted && (
                    <div className="flex shrink-0 gap-1.5">
                      <button
                        type="button"
                        onClick={() => adminDeleteMsg(msg.id)}
                        className="rounded-lg bg-destructive/10 px-2.5 py-1.5 text-[10px] font-bold text-destructive hover:bg-destructive/20"
                      >
                        Delete
                      </button>
                      <button
                        type="button"
                        onClick={() => adminBlockUser(msg.authorStudentId)}
                        className="rounded-lg bg-muted px-2.5 py-1.5 text-[10px] font-bold hover:bg-foreground/10"
                      >
                        Block
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </ChartCard>

        <div className="space-y-4">
          <ChartCard title="Block a Student" icon={<AlertTriangle className="h-4 w-4 text-warning" />}>
            <div className="space-y-2">
              <input
                type="text"
                value={blockReason}
                onChange={(e) => setBlockReason(e.target.value)}
                placeholder="Block reason (optional)"
                className="w-full rounded-xl border border-foreground/10 bg-muted px-3 py-2 text-xs outline-none"
              />
              <p className="text-[10px] text-muted-foreground">Click "Block" next to a message to block that student.</p>
            </div>
          </ChartCard>

          <ChartCard title="Blocked Students" icon={<AlertCircle className="h-4 w-4 text-destructive" />}>
            {blockedUsers.length === 0 ? (
              <p className="text-sm text-muted-foreground">No blocked students.</p>
            ) : (
              <div className="space-y-2">
                {blockedUsers.map((u: any) => (
                  <div key={u.studentId} className="flex items-start gap-3 rounded-xl border border-foreground/8 px-3 py-2.5">
                    <div className="min-w-0 flex-1">
                      <p className="text-[11px] font-bold">{u.studentId}</p>
                      {u.reason && <p className="text-[10px] text-muted-foreground">{u.reason}</p>}
                      <p className="text-[10px] text-muted-foreground">Blocked by {u.blockedBy} · {u.blockedAt}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => adminUnblock(u.studentId)}
                      className="shrink-0 rounded-lg bg-muted px-2.5 py-1.5 text-[10px] font-bold hover:bg-foreground/10"
                    >
                      Unblock
                    </button>
                  </div>
                ))}
              </div>
            )}
          </ChartCard>
        </div>
      </div>
    </div>
  );
}
