import OverviewPanel from "@/roles/admin/panels/OverviewPanel";

// Customer Support home — operational overview (complaints, follow-ups, students).
// Reuses OverviewPanel, which already renders a support-focused role view for the
// "sales" mode.
export default function SupportHome({ state }: { state: any }) {
  return <OverviewPanel state={state} />;
}
