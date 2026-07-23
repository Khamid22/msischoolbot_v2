import { CreditCard } from "lucide-react";
import { ModulePlaceholder } from "@/features/customer-support/placeholders/ModulePlaceholder";

export function PaymentsPlaceholder(props: { authLogin: string; title: string; description: string }) {
  return (
    <ModulePlaceholder
      {...props}
      heading="Payments Workspace"
      detail="The dedicated cross-student payments workspace will be implemented next. Student payment records remain available inside Student profiles."
      icon={CreditCard}
    />
  );
}
