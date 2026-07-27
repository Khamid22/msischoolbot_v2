"""Public HR Manager orchestration interface."""

from backend.modules.domains.recruitment.workspace_contracts import (
    register_hr_manager_recruitment_routes,
)
from backend.modules.people.hr_manager.commands import create_hr_manager_account
from backend.modules.people.hr_manager.module import PERSON_MODULE

__all__ = [
    "PERSON_MODULE",
    "create_hr_manager_account",
    "register_hr_manager_recruitment_routes",
]
