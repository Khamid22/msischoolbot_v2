import TeachersPanel from "@/roles/admin/panels/TeachersPanel";

// HR Manager teacher records. Reuses TeachersPanel (which also contains the
// Hiring/Training candidate pipeline via its internal tabs).
export default function HrTeachers({ state }: { state: any }) {
  return <TeachersPanel state={state} />;
}
