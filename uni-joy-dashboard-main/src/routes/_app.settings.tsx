import { createFileRoute } from "@tanstack/react-router";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/_app/settings")({
  component: SettingsPage,
  head: () => ({ meta: [{ title: "Settings — MSI School Admin" }] }),
});

function SettingsPage() {
  return (
    <>
      <PageHeader title="Settings" description="Configure your admin workspace." />
      <div className="grid gap-4 px-4 md:px-6 pb-8 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Profile</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2"><Label>Display name</Label><Input defaultValue="Khamid A." /></div>
            <div className="grid gap-2"><Label>Email</Label><Input defaultValue="admin@msi.edu" /></div>
            <Button>Save changes</Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Notifications</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {[
              ["New student enrolled", true],
              ["New chat message", true],
              ["Weekly digest", false],
              ["System alerts", true],
            ].map(([label, on]) => (
              <div key={label as string} className="flex items-center justify-between">
                <Label>{label as string}</Label>
                <Switch defaultChecked={on as boolean} />
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
