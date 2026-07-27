"""Public CEO orchestration interface."""

from backend.modules.domains.recruitment.workspace_contracts import register_ceo_recruitment_routes
from backend.modules.domains.reporting.contracts import ceo_workspace_cards
from backend.modules.people.ceo.module import PERSON_MODULE

__all__ = ["PERSON_MODULE", "ceo_workspace_cards", "register_ceo_recruitment_routes"]
