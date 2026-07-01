import OverviewPanel from "@/roles/admin/panels/OverviewPanel";

// CEO home — high-level performance overview (schools, groups, staff, business).
// Reuses the shared OverviewPanel, which already renders the full performance
// dashboard for the "ceo" mode. Kept as a dedicated component so CEO-specific
// composition can diverge later without touching the admin panels.
export default function CeoHome({ state }: { state: any }) {
  return <OverviewPanel state={state} />;
}
