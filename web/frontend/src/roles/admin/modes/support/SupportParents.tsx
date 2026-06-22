import ParentsPanel from "@/roles/admin/panels/ParentsPanel";

// Customer Support parent lookup / communication. Reuses ParentsPanel for now.
export default function SupportParents({ state }: { state: any }) {
  return <ParentsPanel state={state} />;
}
