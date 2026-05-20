import { createFileRoute, Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import {
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Send, Paperclip, Search, MoreVertical, Pin, PinOff, BellOff, Bell, CheckCircle2,
  Trash2, Megaphone, Shield, ShieldOff, Archive, ArchiveRestore,
} from "lucide-react";
import { chats as seedChats } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_app/chat")({
  component: ChatPage,
  head: () => ({ meta: [{ title: "Chat — MSI School Admin" }] }),
});

type Message = {
  id: string;
  from: "student" | "admin";
  text: string;
  time: string;
};

type Thread = {
  id: string;
  studentName: string;
  studentId: string;
  lastMessage: string;
  time: string;
  unread: number;
  pinned: boolean;
  muted: boolean;
  resolved: boolean;
  blocked: boolean;
  archived: boolean;
  messages: Message[];
};

const seedMsgs: Message[] = [
  { id: "m1", from: "student", text: "Hello, when is the next assignment due?", time: "10:21" },
  { id: "m2", from: "admin", text: "Hi! Friday at 23:59. Let me know if you need help.", time: "10:24" },
  { id: "m3", from: "student", text: "Thanks! Can you share the rubric?", time: "10:25" },
  { id: "m4", from: "admin", text: "Sure — uploading it now to Resources.", time: "10:26" },
];

const initialThreads: Thread[] = seedChats.map((c, i) => ({
  id: c.id,
  studentName: c.studentName,
  studentId: c.studentId,
  lastMessage: c.lastMessage,
  time: c.time,
  unread: c.unread,
  pinned: i === 0,
  muted: false,
  resolved: false,
  blocked: false,
  archived: false,
  messages: seedMsgs.map((m) => ({ ...m, text: i === 0 ? m.text : `${m.text}` })),
}));

function ChatPage() {
  const [threads, setThreads] = useState<Thread[]>(initialThreads);
  const [activeId, setActiveId] = useState<string>(threads[0]?.id ?? "");
  const [search, setSearch] = useState("");
  const [draft, setDraft] = useState("");
  const [broadcastOpen, setBroadcastOpen] = useState(false);
  const [broadcastText, setBroadcastText] = useState("");
  const [showArchived, setShowArchived] = useState(false);

  const visibleThreads = useMemo(() => {
    const v = search.trim().toLowerCase();
    return threads
      .filter((t) => (showArchived ? t.archived : !t.archived))
      .filter((t) => !v || t.studentName.toLowerCase().includes(v) || t.studentId.toLowerCase().includes(v))
      .sort((a, b) => Number(b.pinned) - Number(a.pinned));
  }, [threads, search, showArchived]);

  const active = threads.find((t) => t.id === activeId) ?? visibleThreads[0];

  function patch(id: string, p: Partial<Thread>) {
    setThreads((prev) => prev.map((t) => (t.id === id ? { ...t, ...p } : t)));
  }

  function sendMessage() {
    if (!draft.trim() || !active) return;
    const m: Message = {
      id: `m${Date.now()}`,
      from: "admin",
      text: draft.trim(),
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
    patch(active.id, { messages: [...active.messages, m], lastMessage: m.text, time: "now", unread: 0 });
    setDraft("");
  }

  function deleteMessage(threadId: string, msgId: string) {
    const t = threads.find((x) => x.id === threadId);
    if (!t) return;
    patch(threadId, { messages: t.messages.filter((m) => m.id !== msgId) });
  }

  function deleteThread(id: string) {
    setThreads((prev) => prev.filter((t) => t.id !== id));
    if (activeId === id) setActiveId(threads.find((t) => t.id !== id)?.id ?? "");
  }

  function broadcast() {
    if (!broadcastText.trim()) return;
    const text = broadcastText.trim();
    const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    setThreads((prev) =>
      prev.map((t) => ({
        ...t,
        lastMessage: text,
        time: "now",
        messages: [...t.messages, { id: `b${Date.now()}-${t.id}`, from: "admin", text: `📢 ${text}`, time }],
      })),
    );
    setBroadcastText("");
    setBroadcastOpen(false);
  }

  if (!active) {
    return (
      <>
        <PageHeader title="Chat" description="No conversations yet." />
        <div className="px-4 md:px-6 pb-8 text-sm text-muted-foreground">All threads have been deleted.</div>
      </>
    );
  }

  return (
    <TooltipProvider delayDuration={150}>
      <PageHeader
        title="Chat"
        description="Conversations with students from the bot — admin moderation enabled."
        actions={
          <>
            <Button variant="outline" size="sm" asChild>
              <Link to="/announcements"><Megaphone className="h-4 w-4" /> Announcements</Link>
            </Button>

            <Dialog open={broadcastOpen} onOpenChange={setBroadcastOpen}>
              <DialogTrigger asChild>
                <Button size="sm"><Send className="h-4 w-4" /> Broadcast</Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>Broadcast to all conversations</DialogTitle>
                  <DialogDescription>
                    The message will be sent to every active student thread.
                  </DialogDescription>
                </DialogHeader>
                <Textarea rows={5} maxLength={1000} value={broadcastText}
                  onChange={(e) => setBroadcastText(e.target.value)}
                  placeholder="Write a message to everyone…" />
                <p className="text-xs text-muted-foreground">{broadcastText.length}/1000</p>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setBroadcastOpen(false)}>Cancel</Button>
                  <Button onClick={broadcast} disabled={!broadcastText.trim()}>
                    <Send className="h-4 w-4" /> Send to {threads.filter(t => !t.archived).length}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </>
        }
      />

      <div className="px-4 md:px-6 pb-8">
        <Card className="grid h-[calc(100vh-220px)] overflow-hidden md:grid-cols-[320px_1fr]">
          {/* Sidebar */}
          <aside className="flex flex-col border-r border-border">
            <div className="space-y-2 border-b border-border p-3">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input value={search} onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search conversations" className="pl-9 h-9" />
              </div>
              <button
                onClick={() => setShowArchived((v) => !v)}
                className="flex w-full items-center justify-between rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-muted/50"
              >
                <span>{showArchived ? "Archived threads" : "Active threads"}</span>
                <span>{showArchived ? threads.filter(t=>t.archived).length : threads.filter(t=>!t.archived).length}</span>
              </button>
            </div>
            <div className="flex-1 overflow-y-auto">
              {visibleThreads.length === 0 && (
                <p className="p-6 text-center text-sm text-muted-foreground">No conversations.</p>
              )}
              {visibleThreads.map((c) => (
                <button
                  key={c.id}
                  onClick={() => setActiveId(c.id)}
                  className={cn(
                    "flex w-full items-start gap-3 border-b border-border px-3 py-3 text-left transition-colors hover:bg-muted/40",
                    active.id === c.id && "bg-primary-soft/60",
                  )}
                >
                  <div className="relative">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent text-xs font-semibold text-accent-foreground">
                      {c.studentName.split(" ").map((w) => w[0]).slice(0, 2).join("")}
                    </div>
                    {c.pinned && (
                      <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-primary-foreground">
                        <Pin className="h-2.5 w-2.5" />
                      </span>
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <p className="truncate text-sm font-medium">{c.studentName}</p>
                      <span className="shrink-0 text-xs text-muted-foreground">{c.time}</span>
                    </div>
                    <p className="truncate text-xs text-muted-foreground">{c.lastMessage}</p>
                    <div className="mt-1 flex items-center gap-1">
                      {c.muted && <BellOff className="h-3 w-3 text-muted-foreground" />}
                      {c.resolved && <CheckCircle2 className="h-3 w-3 text-success" />}
                      {c.blocked && <Shield className="h-3 w-3 text-destructive" />}
                    </div>
                  </div>
                  {c.unread > 0 && !c.muted && (
                    <Badge className="h-5 min-w-5 justify-center px-1.5 text-xs">{c.unread}</Badge>
                  )}
                </button>
              ))}
            </div>
          </aside>

          {/* Conversation */}
          <section className="flex min-w-0 flex-col">
            <div className="flex items-center gap-3 border-b border-border px-4 py-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-accent text-xs font-semibold text-accent-foreground">
                {active.studentName.split(" ").map((w) => w[0]).slice(0, 2).join("")}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold">{active.studentName}</p>
                <p className="truncate text-xs text-muted-foreground">
                  {active.studentId} ·{" "}
                  {active.blocked ? "blocked" : active.resolved ? "resolved" : "online"}
                </p>
              </div>

              <div className="flex items-center gap-1">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="icon" onClick={() => patch(active.id, { pinned: !active.pinned })}>
                      {active.pinned ? <PinOff className="h-4 w-4" /> : <Pin className="h-4 w-4" />}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>{active.pinned ? "Unpin" : "Pin thread"}</TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="icon" onClick={() => patch(active.id, { muted: !active.muted })}>
                      {active.muted ? <Bell className="h-4 w-4" /> : <BellOff className="h-4 w-4" />}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>{active.muted ? "Unmute" : "Mute"}</TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant={active.resolved ? "secondary" : "ghost"} size="icon"
                      onClick={() => patch(active.id, { resolved: !active.resolved })}
                    >
                      <CheckCircle2 className={cn("h-4 w-4", active.resolved && "text-success")} />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>{active.resolved ? "Reopen" : "Mark resolved"}</TooltipContent>
                </Tooltip>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon"><MoreVertical className="h-4 w-4" /></Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-48">
                    <DropdownMenuItem onClick={() => patch(active.id, { unread: 0 })}>
                      <CheckCircle2 className="h-4 w-4" /> Mark as read
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => patch(active.id, { messages: [] })}>
                      <Trash2 className="h-4 w-4" /> Clear messages
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => patch(active.id, { archived: !active.archived })}>
                      {active.archived
                        ? <><ArchiveRestore className="h-4 w-4" /> Unarchive</>
                        : <><Archive className="h-4 w-4" /> Archive</>}
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => patch(active.id, { blocked: !active.blocked })}>
                      {active.blocked
                        ? <><ShieldOff className="h-4 w-4" /> Unblock student</>
                        : <><Shield className="h-4 w-4" /> Block student</>}
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <DropdownMenuItem
                          onSelect={(e) => e.preventDefault()}
                          className="text-destructive focus:text-destructive"
                        >
                          <Trash2 className="h-4 w-4" /> Delete conversation
                        </DropdownMenuItem>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Delete this conversation?</AlertDialogTitle>
                          <AlertDialogDescription>
                            All messages with {active.studentName} will be permanently removed.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction
                            onClick={() => deleteThread(active.id)}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                          >
                            Delete
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 space-y-3 overflow-y-auto bg-muted/30 p-4">
              {active.messages.length === 0 && (
                <p className="py-10 text-center text-sm text-muted-foreground">No messages yet.</p>
              )}
              {active.messages.map((m) => (
                <div key={m.id} className={cn("group flex items-end gap-2", m.from === "admin" ? "justify-end" : "justify-start")}>
                  {m.from === "admin" && (
                    <button
                      onClick={() => deleteMessage(active.id, m.id)}
                      className="opacity-0 transition-opacity group-hover:opacity-100"
                      aria-label="Delete message"
                    >
                      <Trash2 className="h-3.5 w-3.5 text-muted-foreground hover:text-destructive" />
                    </button>
                  )}
                  <div
                    className={cn(
                      "max-w-[70%] rounded-2xl px-3.5 py-2 text-sm shadow-card",
                      m.from === "admin"
                        ? "rounded-br-sm bg-primary text-primary-foreground"
                        : "rounded-bl-sm bg-surface text-foreground",
                    )}
                  >
                    <p className="whitespace-pre-wrap break-words">{m.text}</p>
                    <p className={cn("mt-1 text-[10px]", m.from === "admin" ? "text-primary-foreground/70" : "text-muted-foreground")}>
                      {m.time}
                    </p>
                  </div>
                  {m.from === "student" && (
                    <button
                      onClick={() => deleteMessage(active.id, m.id)}
                      className="opacity-0 transition-opacity group-hover:opacity-100"
                      aria-label="Delete message"
                    >
                      <Trash2 className="h-3.5 w-3.5 text-muted-foreground hover:text-destructive" />
                    </button>
                  )}
                </div>
              ))}
            </div>

            {/* Composer */}
            {active.blocked ? (
              <div className="border-t border-border bg-destructive/5 px-4 py-3 text-center text-sm text-destructive">
                Student is blocked. Unblock from the menu to resume the conversation.
              </div>
            ) : (
              <form
                onSubmit={(e) => { e.preventDefault(); sendMessage(); }}
                className="flex items-center gap-2 border-t border-border p-3"
              >
                <Button type="button" variant="ghost" size="icon"><Paperclip className="h-4 w-4" /></Button>
                <Input
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder={active.resolved ? "Reply to reopen…" : "Write a message…"}
                  className="flex-1"
                  maxLength={1000}
                />
                <Button type="submit" size="icon" disabled={!draft.trim()}><Send className="h-4 w-4" /></Button>
              </form>
            )}
          </section>
        </Card>
      </div>
    </TooltipProvider>
  );
}
