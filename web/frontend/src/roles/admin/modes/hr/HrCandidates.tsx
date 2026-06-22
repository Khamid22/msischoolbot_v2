import TeachersPanel from "@/roles/admin/panels/TeachersPanel";

// HR Manager candidate / hiring pipeline. The candidate pipeline (Hiring,
// Training, Active stages) currently lives inside TeachersPanel's own tabs, so
// this reuses it for now (rule 9). It is kept as a dedicated component/tab so the
// candidate workflow can be split into its own panel in a later pass.
export default function HrCandidates({ state }: { state: any }) {
  return <TeachersPanel state={state} />;
}
