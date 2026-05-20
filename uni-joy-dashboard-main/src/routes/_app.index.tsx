import { createFileRoute, Link } from "@tanstack/react-router";
import { PageHeader } from "@/components/PageHeader";
import { StatCard } from "@/components/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Users, GraduationCap, BookOpen, MessagesSquare, Plus, ArrowRight } from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { activityWeek, chats, enrollmentTrend, students, teachers, resources } from "@/lib/mock-data";

export const Route = createFileRoute("/_app/")({
  component: Dashboard,
  head: () => ({ meta: [{ title: "Dashboard — MSI School Admin" }] }),
});

function Dashboard() {
  const activeStudents = students.filter((s) => s.status === "active").length;
  const unread = chats.reduce((acc, c) => acc + c.unread, 0);

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Welcome back — here's what's happening at MSI School today."
        actions={
          <>
            <Button variant="outline" size="sm" asChild>
              <Link to="/statistics">View statistics</Link>
            </Button>
            <Button size="sm">
              <Plus className="h-4 w-4" /> Add student
            </Button>
          </>
        }
      />

      <div className="grid gap-4 px-4 md:grid-cols-2 md:px-6 lg:grid-cols-4">
        <StatCard label="Total students" value={students.length * 14} delta={{ value: "+12%", direction: "up" }} icon={Users} tone="primary" />
        <StatCard label="Active today" value={activeStudents * 11} delta={{ value: "+4%", direction: "up" }} icon={GraduationCap} tone="success" />
        <StatCard label="Resources" value={resources.length * 6} delta={{ value: "+8", direction: "up" }} icon={BookOpen} tone="warning" />
        <StatCard label="Unread chats" value={unread} delta={{ value: "-2", direction: "down" }} icon={MessagesSquare} tone="destructive" />
      </div>

      <div className="grid gap-4 px-4 pt-4 md:px-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Enrollment trend</CardTitle>
              <p className="text-sm text-muted-foreground">Monthly active students</p>
            </div>
            <Badge variant="secondary" className="bg-success/10 text-success">+72 this quarter</Badge>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={enrollmentTrend} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--color-primary)" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="var(--color-primary)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                <XAxis dataKey="month" stroke="var(--color-muted-foreground)" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--color-muted-foreground)" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ background: "var(--color-popover)", border: "1px solid var(--color-border)", borderRadius: 8, fontSize: 12 }} />
                <Area type="monotone" dataKey="students" stroke="var(--color-primary)" strokeWidth={2.5} fill="url(#g1)" />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Weekly activity</CardTitle>
            <p className="text-sm text-muted-foreground">Messages & logins</p>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={activityWeek} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                <XAxis dataKey="day" stroke="var(--color-muted-foreground)" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--color-muted-foreground)" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ background: "var(--color-popover)", border: "1px solid var(--color-border)", borderRadius: 8, fontSize: 12 }} />
                <Bar dataKey="messages" fill="var(--color-chart-1)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="logins" fill="var(--color-chart-2)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 px-4 pb-8 pt-4 md:px-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent students</CardTitle>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/students">View all <ArrowRight className="h-4 w-4" /></Link>
            </Button>
          </CardHeader>
          <CardContent className="px-2">
            <div className="divide-y divide-border">
              {students.slice(0, 6).map((s) => (
                <div key={s.id} className="flex items-center gap-3 px-3 py-2.5">
                  <div className="flex h-9 w-9 items-center justify-center rounded-full text-xs font-semibold text-white" style={{ background: s.avatarColor }}>
                    {s.name.split(" ").map((w) => w[0]).slice(0, 2).join("")}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{s.name}</p>
                    <p className="truncate text-xs text-muted-foreground">{s.id} · {s.course}</p>
                  </div>
                  <Badge variant="secondary" className="hidden md:inline-flex">{s.group}</Badge>
                  <span className="hidden text-sm font-medium tabular-nums sm:inline">{s.rating}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Unread messages</CardTitle>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/chat">Open <ArrowRight className="h-4 w-4" /></Link>
            </Button>
          </CardHeader>
          <CardContent className="px-2">
            <div className="divide-y divide-border">
              {chats.slice(0, 5).map((c) => (
                <div key={c.id} className="flex items-start gap-3 px-3 py-2.5">
                  <div className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-full bg-accent text-xs font-semibold text-accent-foreground">
                    {c.studentName.split(" ").map((w) => w[0]).slice(0, 2).join("")}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between">
                      <p className="truncate text-sm font-medium">{c.studentName}</p>
                      <span className="text-xs text-muted-foreground">{c.time}</span>
                    </div>
                    <p className="truncate text-xs text-muted-foreground">{c.lastMessage}</p>
                  </div>
                  {c.unread > 0 && (
                    <Badge className="h-5 min-w-5 justify-center bg-primary px-1.5 text-xs">{c.unread}</Badge>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="hidden">{teachers.length}</div>
    </>
  );
}
