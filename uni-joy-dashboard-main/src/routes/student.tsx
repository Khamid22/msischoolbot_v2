import { createFileRoute, Link } from "@tanstack/react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { BookOpen, Trophy, MessagesSquare, Award, ArrowLeft } from "lucide-react";
import { resources } from "@/lib/mock-data";

export const Route = createFileRoute("/student")({
  component: StudentView,
  head: () => ({ meta: [{ title: "Student view — MSI School" }] }),
});

function StudentView() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-primary-soft/40 to-background">
      <header className="mx-auto flex max-w-3xl items-center justify-between px-4 py-5">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Back to admin
        </Link>
        <Badge variant="secondary">Student preview</Badge>
      </header>

      <main className="mx-auto max-w-3xl space-y-5 px-4 pb-12">
        <Card className="overflow-hidden border-none bg-primary text-primary-foreground shadow-elevated">
          <CardContent className="p-6">
            <p className="text-sm opacity-80">Welcome back,</p>
            <h1 className="mt-1 text-2xl font-semibold">Aiganym Nurlanova</h1>
            <p className="mt-1 text-sm opacity-80">MSI20451 · AI & Data Science</p>
            <div className="mt-5 grid grid-cols-3 gap-3">
              {[
                { label: "Rating", value: "92.4" },
                { label: "Attendance", value: "96%" },
                { label: "Rank", value: "#4" },
              ].map((s) => (
                <div key={s.label} className="rounded-xl bg-white/10 p-3 text-center backdrop-blur">
                  <p className="text-xs opacity-80">{s.label}</p>
                  <p className="mt-1 text-lg font-semibold">{s.value}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { icon: BookOpen, label: "Resources", to: "/" },
            { icon: Trophy, label: "Rating", to: "/" },
            { icon: MessagesSquare, label: "Ask AI", to: "/" },
            { icon: Award, label: "AAP / AR", to: "/" },
          ].map(({ icon: Icon, label }) => (
            <Card key={label} className="cursor-pointer transition-shadow hover:shadow-elevated">
              <CardContent className="flex flex-col items-center gap-2 p-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-soft text-primary">
                  <Icon className="h-5 w-5" />
                </div>
                <span className="text-sm font-medium">{label}</span>
              </CardContent>
            </Card>
          ))}
        </div>

        <Card>
          <CardHeader><CardTitle className="text-base">Course progress</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {[
              { name: "Linear Algebra", v: 78 },
              { name: "Python for ML", v: 64 },
              { name: "Statistics", v: 92 },
            ].map((c) => (
              <div key={c.name}>
                <div className="mb-1.5 flex justify-between text-sm">
                  <span>{c.name}</span>
                  <span className="text-muted-foreground tabular-nums">{c.v}%</span>
                </div>
                <Progress value={c.v} />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">Latest resources</CardTitle>
            <Button variant="ghost" size="sm">See all</Button>
          </CardHeader>
          <CardContent className="space-y-2">
            {resources.slice(0, 4).map((r) => (
              <div key={r.id} className="flex items-center justify-between rounded-lg border border-border p-3">
                <div>
                  <p className="text-sm font-medium">{r.title}</p>
                  <p className="text-xs text-muted-foreground">{r.category}</p>
                </div>
                <Badge variant="secondary">{r.type}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
