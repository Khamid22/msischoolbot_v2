import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Megaphone, Plus, Pin, PinOff, Pencil, Trash2, Send, Users, AlertTriangle, Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_app/announcements")({
  component: AnnouncementsPage,
  head: () => ({ meta: [{ title: "Announcements — MSI School Admin" }] }),
});

type Audience = "all" | "students" | "teachers" | "year10" | "year11";
type Priority = "info" | "important" | "urgent";
type Status = "published" | "draft" | "scheduled";

type Announcement = {
  id: string;
  title: string;
  body: string;
  audience: Audience;
  priority: Priority;
  status: Status;
  pinned: boolean;
  author: string;
  createdAt: string;
  views: number;
};

const audienceLabels: Record<Audience, string> = {
  all: "Everyone",
  students: "All students",
  teachers: "All teachers",
  year10: "Year 10",
  year11: "Year 11",
};

const priorityStyles: Record<Priority, string> = {
  info: "bg-secondary text-secondary-foreground",
  important: "bg-warning/15 text-warning-foreground",
  urgent: "bg-destructive/15 text-destructive",
};

const initialList: Announcement[] = [
  {
    id: "A1",
    title: "Spring midterm exam schedule",
    body: "Midterm exams begin Monday, March 16th. Check the gradebook for your subject schedule. Bring your student ID.",
    audience: "students",
    priority: "important",
    status: "published",
    pinned: true,
    author: "Khamid A.",
    createdAt: "Today · 09:14",
    views: 412,
  },
  {
    id: "A2",
    title: "New AI study assistant in the bot",
    body: "We've added a smarter AI tutor for IGCSE Math. Open the bot and try /ask. Feedback welcome!",
    audience: "all",
    priority: "info",
    status: "published",
    pinned: false,
    author: "Khamid A.",
    createdAt: "Yesterday · 17:02",
    views: 218,
  },
  {
    id: "A3",
    title: "Library closed Friday afternoon",
    body: "The library will close at 13:00 on Friday for maintenance. Reopens Monday at 08:00.",
    audience: "all",
    priority: "urgent",
    status: "published",
    pinned: false,
    author: "Aigerim S.",
    createdAt: "2 days ago",
    views: 96,
  },
  {
    id: "A4",
    title: "Year 11 mock exam prep packet",
    body: "Draft post — link the new PDF before publishing.",
    audience: "year11",
    priority: "info",
    status: "draft",
    pinned: false,
    author: "Khamid A.",
    createdAt: "Draft",
    views: 0,
  },
];

function AnnouncementsPage() {
  const [items, setItems] = useState<Announcement[]>(initialList);
  const [tab, setTab] = useState<"all" | Status>("all");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Announcement | null>(null);

  // Form state
  const [form, setForm] = useState({
    title: "",
    body: "",
    audience: "all" as Audience,
    priority: "info" as Priority,
    pinned: false,
    publishNow: true,
  });

  function openNew() {
    setEditing(null);
    setForm({ title: "", body: "", audience: "all", priority: "info", pinned: false, publishNow: true });
    setOpen(true);
  }

  function openEdit(a: Announcement) {
    setEditing(a);
    setForm({
      title: a.title, body: a.body, audience: a.audience, priority: a.priority,
      pinned: a.pinned, publishNow: a.status === "published",
    });
    setOpen(true);
  }

  function save() {
    if (!form.title.trim() || !form.body.trim()) return;
    if (editing) {
      setItems((prev) => prev.map((p) => p.id === editing.id ? {
        ...p, title: form.title.trim(), body: form.body.trim(), audience: form.audience,
        priority: form.priority, pinned: form.pinned,
        status: form.publishNow ? "published" : "draft",
      } : p));
    } else {
      const a: Announcement = {
        id: `A${Date.now()}`,
        title: form.title.trim(),
        body: form.body.trim(),
        audience: form.audience,
        priority: form.priority,
        pinned: form.pinned,
        status: form.publishNow ? "published" : "draft",
        author: "Khamid A.",
        createdAt: "Just now",
        views: 0,
      };
      setItems((prev) => [a, ...prev]);
    }
    setOpen(false);
  }

  function togglePin(id: string) {
    setItems((prev) => prev.map((p) => p.id === id ? { ...p, pinned: !p.pinned } : p));
  }
  function remove(id: string) {
    setItems((prev) => prev.filter((p) => p.id !== id));
  }
  function publish(id: string) {
    setItems((prev) => prev.map((p) => p.id === id ? { ...p, status: "published", createdAt: "Just now" } : p));
  }

  const filtered = items
    .filter((a) => tab === "all" ? true : a.status === tab)
    .sort((a, b) => Number(b.pinned) - Number(a.pinned));

  const stats = {
    total: items.length,
    published: items.filter((i) => i.status === "published").length,
    drafts: items.filter((i) => i.status === "draft").length,
    reach: items.reduce((acc, i) => acc + i.views, 0),
  };

  return (
    <>
      <PageHeader
        title="Announcements"
        description="Publish news and updates to students and teachers via the bot."
        actions={
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button size="sm" onClick={openNew}><Plus className="h-4 w-4" /> New announcement</Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-lg">
              <DialogHeader>
                <DialogTitle>{editing ? "Edit announcement" : "New announcement"}</DialogTitle>
                <DialogDescription>
                  {editing ? "Update this post and resend if needed." : "It will appear in the bot and on student dashboards."}
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4">
                <div className="grid gap-1.5">
                  <Label htmlFor="t">Title</Label>
                  <Input id="t" value={form.title} maxLength={120}
                    onChange={(e) => setForm({ ...form, title: e.target.value })}
                    placeholder="e.g. Midterm exam schedule" />
                </div>
                <div className="grid gap-1.5">
                  <Label htmlFor="b">Message</Label>
                  <Textarea id="b" rows={5} value={form.body} maxLength={1000}
                    onChange={(e) => setForm({ ...form, body: e.target.value })}
                    placeholder="Write the announcement…" />
                  <p className="text-xs text-muted-foreground">{form.body.length}/1000</p>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="grid gap-1.5">
                    <Label>Audience</Label>
                    <Select value={form.audience} onValueChange={(v) => setForm({ ...form, audience: v as Audience })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {(Object.keys(audienceLabels) as Audience[]).map((k) => (
                          <SelectItem key={k} value={k}>{audienceLabels[k]}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid gap-1.5">
                    <Label>Priority</Label>
                    <Select value={form.priority} onValueChange={(v) => setForm({ ...form, priority: v as Priority })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="info">Info</SelectItem>
                        <SelectItem value="important">Important</SelectItem>
                        <SelectItem value="urgent">Urgent</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="flex items-center justify-between rounded-md border border-border bg-muted/30 px-3 py-2">
                  <div className="flex items-center gap-2 text-sm"><Pin className="h-4 w-4" /> Pin to top</div>
                  <Switch checked={form.pinned} onCheckedChange={(v) => setForm({ ...form, pinned: v })} />
                </div>
                <div className="flex items-center justify-between rounded-md border border-border bg-muted/30 px-3 py-2">
                  <div className="flex items-center gap-2 text-sm"><Send className="h-4 w-4" /> Publish now</div>
                  <Switch checked={form.publishNow} onCheckedChange={(v) => setForm({ ...form, publishNow: v })} />
                </div>
              </div>

              <DialogFooter>
                <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
                <Button onClick={save} disabled={!form.title.trim() || !form.body.trim()}>
                  {editing ? "Save changes" : form.publishNow ? "Publish" : "Save draft"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        }
      />

      <div className="grid gap-4 px-4 md:grid-cols-4 md:px-6">
        <StatTile icon={Megaphone} label="Total" value={stats.total} />
        <StatTile icon={Send} label="Published" value={stats.published} />
        <StatTile icon={Pencil} label="Drafts" value={stats.drafts} />
        <StatTile icon={Users} label="Total reach" value={stats.reach} />
      </div>

      <div className="px-4 md:px-6 pt-4 pb-8">
        <Tabs value={tab} onValueChange={(v) => setTab(v as typeof tab)}>
          <TabsList>
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="published">Published</TabsTrigger>
            <TabsTrigger value="draft">Drafts</TabsTrigger>
            <TabsTrigger value="scheduled">Scheduled</TabsTrigger>
          </TabsList>

          <TabsContent value={tab} className="mt-4 space-y-3">
            {filtered.length === 0 && (
              <Card><CardContent className="py-12 text-center text-sm text-muted-foreground">
                Nothing here yet.
              </CardContent></Card>
            )}
            {filtered.map((a) => (
              <Card key={a.id} className={cn("transition-shadow hover:shadow-elevated", a.pinned && "border-primary/40")}>
                <CardContent className="p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        {a.pinned && <Pin className="h-4 w-4 text-primary" />}
                        <h3 className="font-semibold leading-snug">{a.title}</h3>
                        <Badge variant="secondary" className={priorityStyles[a.priority]}>
                          {a.priority === "urgent" && <AlertTriangle className="h-3 w-3" />}
                          {a.priority === "info" && <Sparkles className="h-3 w-3" />}
                          {a.priority}
                        </Badge>
                        {a.status === "draft" && <Badge variant="outline">Draft</Badge>}
                      </div>
                      <p className="mt-2 whitespace-pre-wrap text-sm text-muted-foreground">{a.body}</p>
                      <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                        <span className="inline-flex items-center gap-1"><Users className="h-3.5 w-3.5" /> {audienceLabels[a.audience]}</span>
                        <span>·</span>
                        <span>{a.author}</span>
                        <span>·</span>
                        <span>{a.createdAt}</span>
                        {a.status === "published" && (<><span>·</span><span>{a.views} views</span></>)}
                      </div>
                    </div>

                    <div className="flex shrink-0 items-center gap-1">
                      {a.status === "draft" && (
                        <Button size="sm" onClick={() => publish(a.id)}>
                          <Send className="h-4 w-4" /> Publish
                        </Button>
                      )}
                      <Button variant="ghost" size="icon" onClick={() => togglePin(a.id)} aria-label="Pin">
                        {a.pinned ? <PinOff className="h-4 w-4" /> : <Pin className="h-4 w-4" />}
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => openEdit(a)} aria-label="Edit">
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button variant="ghost" size="icon" className="text-destructive hover:text-destructive" aria-label="Delete">
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Delete announcement?</AlertDialogTitle>
                            <AlertDialogDescription>
                              This will remove “{a.title}” from the bot and student dashboards. This cannot be undone.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction onClick={() => remove(a.id)} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
                              Delete
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </TabsContent>
        </Tabs>
      </div>
    </>
  );
}

function StatTile({ icon: Icon, label, value }: { icon: typeof Megaphone; label: string; value: number }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 p-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-soft text-primary">
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-xl font-semibold tabular-nums">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}
