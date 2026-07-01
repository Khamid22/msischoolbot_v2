import AcademicPanel from "@/roles/admin/panels/AcademicPanel";

// CEO school/group performance. Reuses the existing AcademicPanel "groups" view
// for now (rule 9: reuse is acceptable for this structural pass).
export default function CeoGroups({ state }: { state: any }) {
  return <AcademicPanel state={state} kind="groups" />;
}
