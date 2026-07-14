import { asString } from "@/shared/lib/workspace";
import { RoleOverviewPanel } from "./overview/RoleOverviewPanel";
import { SchoolOverviewPanel } from "./overview/SchoolOverviewPanel";

export default function OverviewPanel({ state }: { state: any }) {
  if (!["admin", "ceo"].includes(asString(state.adminMode).toLowerCase())) {
    return <RoleOverviewPanel state={state} />;
  }
  return <SchoolOverviewPanel state={state} />;
}

