import CareerGrowthPanel from "@/roles/admin/panels/CareerGrowthPanel";

// HR Manager career growth / training & status. Reuses CareerGrowthPanel.
export default function HrCareerGrowth({ state }: { state: any }) {
  return <CareerGrowthPanel state={state} />;
}
