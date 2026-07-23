import { LayoutDashboard } from "lucide-react";
import { ModulePlaceholder } from "@/features/customer-support/placeholders/ModulePlaceholder";

export function DashboardPlaceholder(props: { authLogin: string; title: string; description: string }) {
  return (
    <ModulePlaceholder
      {...props}
      heading="Customer Support Dashboard"
      detail="Operational summary will be implemented in the next phase."
      icon={LayoutDashboard}
    />
  );
}
