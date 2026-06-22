import ComplaintsPanel from "@/roles/admin/panels/ComplaintsPanel";

// Customer Support complaint queue. Reuses ComplaintsPanel for now.
export default function SupportComplaints({ state }: { state: any }) {
  return <ComplaintsPanel state={state} />;
}
