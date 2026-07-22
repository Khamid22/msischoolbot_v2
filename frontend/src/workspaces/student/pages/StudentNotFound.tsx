import { AlertCircle } from "lucide-react";
import { CenteredPage } from "@/shared/ui/PortalCard";

interface StudentNotFoundProps {
  message?: string;
  returnUrl?: string;
}

export default function StudentNotFound(props: StudentNotFoundProps) {
  return (
    <CenteredPage title="Student Not Found" subtitle={props.message || "We could not retrieve data for this student. Please search again."}>
      <div className="flex flex-col items-center text-center">
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-destructive/10 text-destructive">
          <AlertCircle className="h-7 w-7" />
        </div>
        <a
          href={props.returnUrl || "/"}
          className="rounded-xl bg-primary px-6 py-3 text-sm font-bold text-primary-foreground shadow-neo transition-all active:translate-x-[0.0625rem] active:translate-y-[0.0625rem] active:shadow-none"
        >
          Return to Search
        </a>
      </div>
    </CenteredPage>
  );
}
