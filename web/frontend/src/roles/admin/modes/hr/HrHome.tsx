import OverviewPanel from "@/roles/admin/panels/OverviewPanel";

// HR Manager home — hiring pipeline and staff overview. Reuses OverviewPanel,
// which already renders an HR-focused role view (candidate pipeline metrics) for
// the "hr" mode.
export default function HrHome({ state }: { state: any }) {
  return <OverviewPanel state={state} />;
}
