import StudentsPanel from "@/roles/admin/panels/StudentsPanel";

// Customer Support student lookup. Reuses StudentsPanel for now.
export default function SupportStudents({ state }: { state: any }) {
  return <StudentsPanel state={state} />;
}
