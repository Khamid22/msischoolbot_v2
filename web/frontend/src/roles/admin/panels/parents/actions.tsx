import { Eye, KeyRound, Link2, Link2Off, Pencil, Power, PowerOff, Trash2 } from "lucide-react";
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
  onEdit: (parent: ParentRow) => void;
  onLinkStudent: (parent: ParentRow) => void;
  onUnlinkStudent: (parent: ParentRow) => void;
  onUnlinkChild: (parent: ParentRow, child: ParentRow) => void;
  onResetPassword: (parent: ParentRow) => void;
  onToggleDisabled: (parent: ParentRow) => void;
  onDelete: (parent: ParentRow) => void;
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
 * Build the three-dot menu for a parent row. Invite-link rows are not real
 * admin records, so account-management actions are omitted for them.
 */
export function buildParentMenuItems(parent: ParentRow, handlers: ParentHandlers): ActionMenuItem[] {
  const invite = isInviteSource(parent);
  const linked = isLinked(parent);
  const disabled = isDisabled(parent);

  const items: ActionMenuItem[] = [
    {
      key: "view",
      label: "View profile",
      icon: <Eye className="h-4 w-4" />,
      onClick: () => handlers.onView(parent),
    },
  ];

  if (!invite) {
    items.push({
      key: "edit",
      label: "Edit parent",
      icon: <Pencil className="h-4 w-4" />,
      onClick: () => handlers.onEdit(parent),
    });
    items.push({
      key: "link",
      label: "Link student",
      icon: <Link2 className="h-4 w-4" />,
      onClick: () => handlers.onLinkStudent(parent),
    });
    items.push({
      key: "unlink",
      label: "Unlink student",
      icon: <Link2Off className="h-4 w-4" />,
      onClick: () => handlers.onUnlinkStudent(parent),
      disabled: !linked,
      tooltip: linked ? undefined : "No linked students",
    });
  }

  if (!invite) {
    items.push({ key: "sep-1", separator: true });
    items.push({
      key: "reset",
      label: "Reset password",
      icon: <KeyRound className="h-4 w-4" />,
      onClick: () => handlers.onResetPassword(parent),
    });
    items.push({
      key: "toggle",
      label: disabled ? "Enable account" : "Disable account",
      icon: disabled ? <Power className="h-4 w-4" /> : <PowerOff className="h-4 w-4" />,
      onClick: () => handlers.onToggleDisabled(parent),
    });
    items.push({
      key: "delete",
      label: "Delete account",
      icon: <Trash2 className="h-4 w-4" />,
      onClick: () => handlers.onDelete(parent),
      danger: true,
    });
  }

  return items;
}
