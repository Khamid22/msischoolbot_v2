"""HR Manager Recruitment workspace page registration."""

from fastapi import FastAPI

from backend.modules.people.hr_manager.contracts import register_hr_manager_recruitment_routes


def register_hr_manager_page_routes(app: FastAPI) -> None:
    register_hr_manager_recruitment_routes(app)


__all__ = ["register_hr_manager_page_routes"]
