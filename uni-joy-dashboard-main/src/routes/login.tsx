import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { LogIn } from "lucide-react";

export const Route = createFileRoute("/login")({
  component: LoginPage,
  head: () => ({ meta: [{ title: "Sign in — MSI School" }] }),
});

function LoginPage() {
  const navigate = useNavigate();
  const [login, setLogin] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (login.toLowerCase().startsWith("msi")) navigate({ to: "/student" });
    else navigate({ to: "/" });
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-primary-soft via-background to-accent p-4">
      <Card className="w-full max-w-md shadow-elevated">
        <CardHeader className="text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground text-lg font-bold">
            M
          </div>
          <CardTitle className="text-xl">MSI School</CardTitle>
          <p className="text-sm text-muted-foreground">Sign in to your account</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-4">
            <div className="grid gap-2">
              <Label htmlFor="login">Login</Label>
              <Input id="login" value={login} onChange={(e) => setLogin(e.target.value)} placeholder="staff##### or MSI#####" required />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="pw">Password</Label>
              <Input id="pw" type="password" placeholder="••••••••" required />
            </div>
            <Button type="submit" className="w-full">
              <LogIn className="h-4 w-4" /> Sign in
            </Button>
            <p className="text-center text-xs text-muted-foreground">
              Staff IDs start with <code className="rounded bg-muted px-1">staff</code>, students with <code className="rounded bg-muted px-1">MSI</code>.
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
