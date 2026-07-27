"""Public transport contracts for person-owned Recruitment workspaces."""

from fastapi import FastAPI

from backend.modules.domains.recruitment.page import _register_role_routes


def register_hr_manager_recruitment_routes(app: FastAPI) -> None:
    _register_role_routes(
        app,
        role="hr_manager",
        base_path="/hr-manager",
        operation_prefix="hr_manager",
        include_settings=True,
        include_trash=True,
        include_rejected=True,
        include_analytics=True,
        include_teachers=True,
    )


def register_ceo_recruitment_routes(app: FastAPI) -> None:
    _register_role_routes(
        app,
        role="ceo",
        base_path="/ceo/recruitment",
        operation_prefix="ceo",
        include_analytics=True,
        include_settings=True,
    )


def register_academic_director_recruitment_routes(app: FastAPI) -> None:
    _register_role_routes(
        app,
        role="academic_director",
        base_path="/academic-director/recruitment",
        operation_prefix="academic_director",
        root_view="candidates",
        include_pipeline=False,
        include_tasks=False,
        redirect_decisions_to_candidates=True,
    )


def register_head_of_department_recruitment_routes(app: FastAPI) -> None:
    _register_role_routes(
        app,
        role="head_of_department",
        base_path="/head-of-departments/recruitment",
        operation_prefix="head_of_department",
        root_view="candidates",
        include_pipeline=False,
        include_tasks=False,
    )


__all__ = [
    "register_academic_director_recruitment_routes",
    "register_ceo_recruitment_routes",
    "register_head_of_department_recruitment_routes",
    "register_hr_manager_recruitment_routes",
]
