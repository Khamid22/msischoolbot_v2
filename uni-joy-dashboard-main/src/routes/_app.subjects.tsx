import { createFileRoute, Link } from "@tanstack/react-router";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Plus, BookMarked, Layers, MoreHorizontal } from "lucide-react";
import { subjects } from "@/lib/academic-data";

export const Route = createFileRoute("/_app/subjects")({
  component: SubjectsPage,
  head: () => ({ meta: [{ title: "Subjects — MSI School Admin" }] }),
});

function SubjectsPage() {
  return (
    <>
      <PageHeader
        title="Subjects"
        description="IGCSE syllabus subjects taught at MSI School."
        actions={
          <>
            <Button variant="outline" size="sm">Import syllabus</Button>
            <Button size="sm"><Plus className="h-4 w-4" /> Add subject</Button>
          </>
        }
      />

      <div className="grid gap-4 px-4 md:grid-cols-2 md:px-6 pb-8 lg:grid-cols-3">
        {subjects.map((s) => (
          <Card key={s.id} className="group transition-shadow hover:shadow-elevated">
            <CardContent className="p-5">
              <div className="flex items-start justify-between">
                <div
                  className="flex h-11 w-11 items-center justify-center rounded-xl text-white"
                  style={{ background: s.color }}
                >
                  <BookMarked className="h-5 w-5" />
                </div>
                <Button variant="ghost" size="icon" className="h-8 w-8 opacity-0 transition-opacity group-hover:opacity-100">
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </div>

              <div className="mt-4">
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="font-mono text-[10px]">{s.code}</Badge>
                  <Badge variant="secondary">{s.level}</Badge>
                </div>
                <h3 className="mt-2 font-semibold leading-snug">{s.name}</h3>
                <p className="mt-1 text-xs text-muted-foreground">Lead: {s.teacher}</p>
              </div>

              <div className="mt-4 flex items-center justify-between border-t border-border pt-3">
                <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  <Layers className="h-4 w-4" /> {s.groups} groups
                </div>
                <Button variant="ghost" size="sm" asChild>
                  <Link to="/groups">Open groups</Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
