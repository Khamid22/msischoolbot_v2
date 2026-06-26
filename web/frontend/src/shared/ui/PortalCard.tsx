import { ReactNode } from "react";
import { GraduationCap } from "lucide-react";
import { motion } from "@/shared/lib/motion";

interface CenteredPageProps {
  title: string;
  subtitle: string;
  children: ReactNode;
}

export function CenteredPage({ title, subtitle, children }: CenteredPageProps) {
  return (
    <div
      className="flex app-height flex-col overflow-y-auto bg-background"
      style={{
        paddingTop: "calc(var(--app-top-inset) + 1rem)",
        paddingRight: "max(0.75rem, calc(var(--app-right-inset) + 0.5rem))",
        paddingBottom: "calc(var(--app-bottom-inset) + 1rem)",
        paddingLeft: "max(0.75rem, calc(var(--app-left-inset) + 0.5rem))",
        overscrollBehaviorY: "contain",
        WebkitOverflowScrolling: "touch",
      }}
    >
      <div className="flex min-h-full flex-1 items-center justify-center">
        <div className="w-full max-w-md">
          <div className={`rounded-3xl border border-primary/10 bg-surface/95 p-6 shadow-card sm:p-8 ${motion.panel}`}>
            <div className="mb-6 text-center">
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-foreground text-background shadow-card">
                <GraduationCap className="h-7 w-7" />
              </div>
              <h1 className="font-display text-xl font-bold sm:text-2xl">{title}</h1>
              <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
            </div>
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}

export function FormAlert({
  kind,
  children,
}: {
  kind: "error" | "notice";
  children: ReactNode;
}) {
  const classes =
    kind === "error"
      ? "border-destructive/20 bg-destructive/5 text-destructive"
      : "border-success/20 bg-success/10 text-foreground";

  return (
    <div className={`mb-4 rounded-xl border px-4 py-3 text-sm font-medium ${classes}`}>
      {children}
    </div>
  );
}
