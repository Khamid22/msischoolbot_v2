import PaymentsPanel from "@/roles/admin/panels/PaymentsPanel";

// Customer Support payments / follow-up. Reuses PaymentsPanel for now.
export default function SupportPayments({ state }: { state: any }) {
  return <PaymentsPanel state={state} />;
}
