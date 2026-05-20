import { createFileRoute } from "@tanstack/react-router";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Plus, Mail, Users2 } from "lucide-react";
import { teachers } from "@/lib/mock-data";

export const Route = createFileRoute("/_app/teachers")({
  component: TeachersPage,
  head: () => ({ meta: [{ title: "Teachers — MSI School Admin" }] }),
});

function TeachersPage() {
  return (
    <>
      <PageHeader
        title="Teachers"
        description="Manage faculty, subjects and group assignments."
        actions={<Button size="sm"><Plus className="h-4 w-4" /> Add teacher</Button>}
      />
      <div className="grid gap-4 px-4 md:grid-cols-2 md:px-6 pb-8 lg:grid-cols-3">
        {teachers.map((t) => (
          <Card key={t.id} className="transition-shadow hover:shadow-elevated">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-full bg-primary-soft text-sm font-semibold text-primary">
                    {t.name.split(" ").map((w) => w[0]).slice(0, 2).join("")}
                  </div>
                  <div>
                    <CardTitle className="text-base">{t.name}</CardTitle>
                    <p className="text-xs text-muted-foreground">{t.id}</p>
                  </div>
                </div>
                <Badge variant="secondary">{t.subject}</Badge>
              </div>
            </CardHeader>
            <CardContent className="flex items-center justify-between border-t border-border pt-4">
              <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <Users2 className="h-4 w-4" /> {t.groups} groups
              </div>
              <Button variant="ghost" size="sm">
                <Mail className="h-4 w-4" /> Contact
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
