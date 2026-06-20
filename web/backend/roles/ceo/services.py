"""CEO role service facade."""

from web.backend.roles.admin.services.insights_service import (  # noqa: F401
    build_admin_group_highlights,
    build_admin_quick_stats,
    build_admin_school_info,
    build_admin_subject_info,
)
from web.backend.domains.academics.internal_dashboard_service import (  # noqa: F401
    build_internal_overview_dataset,
)

__all__ = [
    "build_admin_group_highlights",
    "build_admin_quick_stats",
    "build_admin_school_info",
    "build_admin_subject_info",
    "build_internal_overview_dataset",
]

