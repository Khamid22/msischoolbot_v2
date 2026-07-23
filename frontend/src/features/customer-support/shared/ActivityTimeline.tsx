import type { SupportAuditEvent } from "@/features/customer-support/model";
import { formatDate } from "@/features/customer-support/shared/ui";

export function ActivityTimeline({ items }: { items: SupportAuditEvent[] }) {
  if (!items.length) {
    return <p className="text-sm font-semibold text-muted-foreground">No Customer Support changes have been recorded yet.</p>;
  }

  return (
    <ol className="space-y-3">
      {items.map((item) => (
        <li key={item.id} className="relative border-l-2 border-primary/20 pl-4">
          <span className="absolute -left-[0.3125rem] top-1.5 h-2 w-2 rounded-full bg-primary" aria-hidden="true" />
          <p className="break-words text-sm font-black text-foreground">
            {item.eventType.replace(/\./g, " · ").replace(/_/g, " ")}
          </p>
          <p className="mt-0.5 text-xs font-semibold text-muted-foreground">
            {item.actor} · {formatDate(item.createdAt, true)}
          </p>
        </li>
      ))}
    </ol>
  );
}
