import TeachersPanel from "@/roles/admin/panels/TeachersPanel";

// HR Manager teacher records only. Candidates live in the Candidates tab.
export default function HrTeachers({ state }: { state: any }) {
  return <TeachersPanel state={state} view="teachers" />;
}
