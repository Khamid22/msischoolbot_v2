import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Plus, Search, MoreHorizontal, Mail, Pencil } from "lucide-react";
import { students } from "@/lib/mock-data";

export const Route = createFileRoute("/_app/students")({
  component: StudentsPage,
  head: () => ({ meta: [{ title: "Students — MSI School Admin" }] }),
});

function StudentsPage() {
  const [q, setQ] = useState("");
  const [tab, setTab] = useState("all");

  const filtered = useMemo(() => {
    return students.filter((s) => {
      if (tab === "active" && s.status !== "active") return false;
      if (tab === "inactive" && s.status !== "inactive") return false;
      if (!q) return true;
      const v = q.toLowerCase();
      return s.name.toLowerCase().includes(v) || s.id.toLowerCase().includes(v) || s.course.toLowerCase().includes(v);
    });
  }, [q, tab]);

  return (
    <>
      <PageHeader
        title="Students"
        description="Manage every student enrolled at MSI School."
        actions={
          <>
            <Button variant="outline" size="sm">Import CSV</Button>
            <Button size="sm"><Plus className="h-4 w-4" /> Add student</Button>
          </>
        }
      />

      <div className="px-4 md:px-6 pb-8">
        <Card className="overflow-hidden">
          <div className="flex flex-col gap-3 border-b border-border p-4 md:flex-row md:items-center md:justify-between">
            <Tabs value={tab} onValueChange={setTab}>
              <TabsList>
                <TabsTrigger value="all">All <span className="ml-1.5 text-xs text-muted-foreground">{students.length}</span></TabsTrigger>
                <TabsTrigger value="active">Active</TabsTrigger>
                <TabsTrigger value="inactive">Inactive</TabsTrigger>
              </TabsList>
            </Tabs>
            <div className="relative md:w-72">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name, ID, course" className="pl-9" />
            </div>
          </div>

          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40">
                <TableHead>Student</TableHead>
                <TableHead className="hidden md:table-cell">Course</TableHead>
                <TableHead>Group</TableHead>
                <TableHead className="text-right">Rating</TableHead>
                <TableHead className="hidden lg:table-cell text-right">Attendance</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((s) => (
                <TableRow key={s.id} className="hover:bg-muted/30">
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 items-center justify-center rounded-full text-xs font-semibold text-white" style={{ background: s.avatarColor }}>
                        {s.name.split(" ").map((w) => w[0]).slice(0, 2).join("")}
                      </div>
                      <div>
                        <p className="font-medium">{s.name}</p>
                        <p className="text-xs text-muted-foreground">{s.id}</p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="hidden md:table-cell text-sm text-muted-foreground">{s.course}</TableCell>
                  <TableCell><Badge variant="secondary">{s.group}</Badge></TableCell>
                  <TableCell className="text-right font-medium tabular-nums">{s.rating}</TableCell>
                  <TableCell className="hidden lg:table-cell text-right tabular-nums text-muted-foreground">{s.attendance}%</TableCell>
                  <TableCell>
                    {s.status === "active" ? (
                      <Badge className="bg-success/15 text-success hover:bg-success/15">Active</Badge>
                    ) : (
                      <Badge variant="secondary" className="text-muted-foreground">Inactive</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button variant="ghost" size="icon" className="h-8 w-8"><Mail className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8"><Pencil className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8"><MoreHorizontal className="h-4 w-4" /></Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="py-12 text-center text-sm text-muted-foreground">
                    No students match your search.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Card>
      </div>
    </>
  );
}
