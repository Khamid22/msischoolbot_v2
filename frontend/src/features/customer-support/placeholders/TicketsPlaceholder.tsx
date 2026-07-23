import { TicketCheck } from "lucide-react";
import { ModulePlaceholder } from "@/features/customer-support/placeholders/ModulePlaceholder";

export function TicketsPlaceholder(props: { authLogin: string; title: string; description: string }) {
  return (
    <ModulePlaceholder
      {...props}
      heading="Support Tickets"
      detail="Ticket intake and workflow will be implemented after Parents and Students."
      icon={TicketCheck}
    />
  );
}
