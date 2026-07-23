import type { LucideIcon } from "lucide-react";
import { ShieldCheck } from "lucide-react";
import { PageHeader } from "@/shared/ui/PageHeader";

export function ModulePlaceholder({
  authLogin,
  title,
  description,
  heading,
  detail,
  icon: Icon,
}: {
  authLogin: string;
  title: string;
  description: string;
  heading: string;
  detail: string;
  icon: LucideIcon;
}) {
  return (
    <div className="flex min-w-0 flex-col gap-4 overflow-x-hidden">
      <PageHeader
        title={title}
        subtitle={description}
        badge={<span className="rounded-full bg-primary/10 px-2.5 py-1 text-[0.6875rem] font-black uppercase tracking-wide text-primary">Customer Support</span>}
        actions={authLogin ? (
          <span className="inline-flex min-h-10 max-w-full items-center gap-2 rounded-lg border border-border bg-muted px-3 text-xs font-black text-muted-foreground">
            <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-600" aria-hidden="true" />
            <span className="truncate">{authLogin}</span>
          </span>
        ) : undefined}
      />
      <section className="rounded-lg border border-border bg-card p-6 shadow-card sm:p-8">
        <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Icon className="h-6 w-6" aria-hidden="true" />
        </span>
        <h1 className="mt-5 text-xl font-black text-foreground">{heading}</h1>
        <p className="mt-2 max-w-2xl text-sm font-semibold leading-6 text-muted-foreground">{detail}</p>
        <span className="mt-5 inline-flex rounded-full border border-border bg-muted px-3 py-1 text-xs font-black uppercase tracking-wide text-muted-foreground">
          Planned next phase
        </span>
      </section>
    </div>
  );
}
