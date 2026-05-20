import { createFileRoute } from "@tanstack/react-router";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FileText, Film, Link as LinkIcon, FileType, Upload, Eye, MoreHorizontal } from "lucide-react";
import { resources } from "@/lib/mock-data";

export const Route = createFileRoute("/_app/resources")({
  component: ResourcesPage,
  head: () => ({ meta: [{ title: "Resources — MSI School Admin" }] }),
});

const iconMap = { PDF: FileText, Video: Film, Link: LinkIcon, Doc: FileType };

function ResourcesPage() {
  return (
    <>
      <PageHeader
        title="Resources"
        description="Upload and organize study materials for every course."
        actions={<Button size="sm"><Upload className="h-4 w-4" /> Upload</Button>}
      />
      <div className="grid gap-4 px-4 md:grid-cols-2 md:px-6 pb-8 lg:grid-cols-3">
        {resources.map((r) => {
          const Icon = iconMap[r.type];
          return (
            <Card key={r.id} className="group transition-shadow hover:shadow-elevated">
              <CardContent className="p-5">
                <div className="flex items-start justify-between">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-accent text-accent-foreground">
                    <Icon className="h-5 w-5" />
                  </div>
                  <Button variant="ghost" size="icon" className="h-8 w-8 opacity-0 transition-opacity group-hover:opacity-100">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </div>
                <h3 className="mt-4 font-semibold leading-snug">{r.title}</h3>
                <p className="mt-1 text-xs text-muted-foreground">{r.category}</p>
                <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground">
                  <Badge variant="secondary">{r.type}</Badge>
                  <div className="flex items-center gap-3">
                    <span className="flex items-center gap-1"><Eye className="h-3.5 w-3.5" /> {r.views}</span>
                    <span>{r.uploaded}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </>
  );
}
