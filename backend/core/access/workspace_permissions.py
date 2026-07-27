"""Fine-grained feature permissions used by browser workspace guards."""

from backend.core.access import roles
from backend.core.access.capabilities import capabilities_for_role, role_has_capability


ROLE_FEATURE_PERMISSIONS = {
    role: {capability.value for capability in capabilities_for_role(role)}
    for role in roles.ALL_ROLES
}


def has_workspace_permission(role, permission) -> bool:
    normalized_role = roles.normalize_role(role)
    normalized_permission = str(permission or "").strip()
    if not normalized_role or not normalized_permission:
        return False
    return role_has_capability(normalized_role, normalized_permission)
