import { createFileRoute, Link } from "@tanstack/react-router";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Plus, Users, ArrowRight } from "lucide-react";
import { groups, subjects } from "@/lib/academic-data";

export const Route = createFileRoute("/_app/groups/")({
  component: GroupsPage,
  head: () => ({ meta: [{ title: "Groups — MSI School Admin" }] }),
});

function GroupsPage() {
  return (
    <>
      <PageHeader
        title="Groups"
        description="Class groups and their gradebooks. Open a group to edit scores & attendance."
        actions={<Button size="sm"><Plus className="h-4 w-4" /> Create group</Button>}
      />

      <div className="grid gap-4 px-4 md:grid-cols-2 md:px-6 pb-8 lg:grid-cols-3">
        {groups.map((g) => {
          const subject = subjects.find((s) => s.id === g.subjectId);
          return (
            <Card key={g.id} className="group transition-shadow hover:shadow-elevated">
              <CardContent className="p-5">
                <div className="flex items-start gap-3">
                  <div
                    className="h-10 w-10 shrink-0 rounded-lg"
                    style={{ background: subject?.color ?? "var(--color-primary)" }}
                  />
                  <div className="min-w-0 flex-1">
                    <h3 className="truncate font-semibold">{g.name}</h3>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {subject?.code} · {g.yearLevel}
                    </p>
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-between border-t border-border pt-3">
                  <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                    <Users className="h-4 w-4" /> {g.studentIds.length} students
                  </div>
                  <Button variant="ghost" size="sm" asChild>
                    <Link to="/groups/$groupId" params={{ groupId: g.id }}>
                      Gradebook <ArrowRight className="h-4 w-4" />
                    </Link>
                  </Button>
                </div>

                <div className="mt-3 flex flex-wrap gap-1.5">
                  <Badge variant="secondary" className="text-xs">Attendance</Badge>
                  <Badge variant="secondary" className="text-xs">7 assessments</Badge>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </>
  );
}
