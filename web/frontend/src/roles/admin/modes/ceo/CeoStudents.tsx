import StudentsPanel from "@/roles/admin/panels/StudentsPanel";

// CEO student risk overview. Reuses StudentsPanel for now.
export default function CeoStudents({ state }: { state: any }) {
  return <StudentsPanel state={state} />;
}
