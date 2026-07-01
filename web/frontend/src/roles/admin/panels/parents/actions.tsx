import { Eye, Link2, Link2Off, Ticket } from "lucide-react";
import { Badge } from "@/shared/ui/Badge";
import { type ActionMenuItem } from "@/shared/ui/ActionMenu";
import {
  type ParentRow,
  isDisabled,
  isInviteSource,
  isLinked,
} from "./types";

export interface ParentHandlers {
  onView: (parent: ParentRow) => void;
  onLinkStudent: (parent: ParentRow) => void;
  onUnlinkStudent: (parent: ParentRow) => void;
  onUnlinkChild: (parent: ParentRow, child: ParentRow) => void;
  onOpenTickets: (parent: ParentRow) => void;
}

/** Primary account/link status badges shown in the Account status column and drawer. */
export function ParentStatusBadges({ parent }: { parent: ParentRow }) {
  const invite = isInviteSource(parent);
  const disabled = isDisabled(parent);
  return (
    <div className="flex flex-wrap items-center gap-1">
      {disabled ? (
        <Badge tone="danger">Disabled</Badge>
      ) : invite ? (
        <Badge tone="info">Registered</Badge>
      ) : (
        <Badge tone="success">Active</Badge>
      )}
      {!isLinked(parent) ? <Badge tone="warning">Not linked</Badge> : null}
    </div>
  );
}

/**
 * Build the three-dot menu for a parent row. Parent accounts are invite-led,
 * so staff can inspect, link students, unlink students, and open support only.
 */
export function buildParentMenuItems(parent: ParentRow, handlers: ParentHandlers): ActionMenuItem[] {
  const linked = isLinked(parent);

  const items: ActionMenuItem[] = [
    {
      key: "view",
      label: "View profile",
      icon: <Eye className="h-4 w-4" />,
      onClick: () => handlers.onView(parent),
    },
    {
      key: "link",
      label: "Link student",
      icon: <Link2 className="h-4 w-4" />,
      onClick: () => handlers.onLinkStudent(parent),
    },
    {
      key: "unlink",
      label: "Unlink student",
      icon: <Link2Off className="h-4 w-4" />,
      onClick: () => handlers.onUnlinkStudent(parent),
      disabled: !linked,
      tooltip: linked ? undefined : "No linked students",
    },
    {
      key: "tickets",
      label: "Open tickets",
      icon: <Ticket className="h-4 w-4" />,
      onClick: () => handlers.onOpenTickets(parent),
    },
  ];

  return items;
}
