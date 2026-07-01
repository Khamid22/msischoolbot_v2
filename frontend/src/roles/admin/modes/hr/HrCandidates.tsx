import TeachersPanel from "@/roles/admin/panels/TeachersPanel";

// HR Manager candidate workflow: hiring pipeline and training only.
export default function HrCandidates({ state }: { state: any }) {
  return <TeachersPanel state={state} view="candidates" />;
}
