"""Browser page adapters for the shared recruitment workspace."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from backend.core.access.pages import require_role
from backend.core.web.rendering import generate_csrf, render_react_page
from backend.modules.identity.session import current_auth_login, current_auth_role


def _render(*, role: str, view: str, base_path: str, candidate_id: int | None = None):
    return render_react_page(
        "recruitment-workspace",
        {
            "authLogin": current_auth_login(),
            "authRole": current_auth_role(),
            "role": role,
            "view": view,
            "basePath": base_path,
            "candidateId": candidate_id,
            "csrfToken": generate_csrf(),
        },
        title="Teacher Recruitment | MSI School",
        description="Role-aware teacher recruitment pipeline and candidate workspace.",
        telegram=True,
    )


def _register_role_routes(
    app,
    *,
    role: str,
    base_path: str,
    operation_prefix: str,
    root_view: str = "pipeline",
    include_decisions: bool = False,
    include_settings: bool = False,
    include_trash: bool = False,
    include_rejected: bool = False,
) -> None:
    router = APIRouter(dependencies=[Depends(require_role(role))])

    @router.get(base_path, operation_id=f"{operation_prefix}_recruitment")
    def root():
        return _render(role=role, view=root_view, base_path=base_path)

    @router.get(f"{base_path}/pipeline", operation_id=f"{operation_prefix}_recruitment_pipeline")
    def pipeline():
        return _render(role=role, view="pipeline", base_path=base_path)

    @router.get(f"{base_path}/candidates", operation_id=f"{operation_prefix}_recruitment_candidates")
    def candidates(request: Request):
        if role == "hr_manager":
            suffix = f"?{request.query_params}" if request.query_params else ""
            return RedirectResponse(f"{base_path}/pipeline{suffix}", status_code=307)
        return _render(role=role, view="candidates", base_path=base_path)

    @router.get(f"{base_path}/schedule", operation_id=f"{operation_prefix}_recruitment_schedule")
    def schedule():
        return _render(role=role, view="schedule", base_path=base_path)

    @router.get(f"{base_path}/tasks", operation_id=f"{operation_prefix}_recruitment_tasks")
    def tasks(request: Request):
        if role == "hr_manager":
            suffix = f"?{request.query_params}" if request.query_params else ""
            return RedirectResponse(f"{base_path}/pipeline{suffix}", status_code=307)
        return _render(role=role, view="tasks", base_path=base_path)

    if include_rejected:

        @router.get(
            f"{base_path}/rejected",
            operation_id=f"{operation_prefix}_recruitment_rejected",
        )
        def rejected():
            return _render(role=role, view="rejected", base_path=base_path)

    if include_decisions:

        @router.get(
            f"{base_path}/decisions",
            operation_id=f"{operation_prefix}_recruitment_decisions",
        )
        def decisions():
            return _render(role=role, view="decisions", base_path=base_path)

    if include_settings:

        @router.get(
            f"{base_path}/settings",
            operation_id=f"{operation_prefix}_recruitment_settings",
        )
        def settings():
            return _render(role=role, view="settings", base_path=base_path)

    if include_trash:

        @router.get(
            f"{base_path}/trash",
            operation_id=f"{operation_prefix}_recruitment_trash",
        )
        def trash():
            return _render(role=role, view="trash", base_path=base_path)

    @router.get(f"{base_path}/profile", operation_id=f"{operation_prefix}_recruitment_profile")
    def profile():
        return _render(role=role, view="profile", base_path=base_path)

    @router.get(
        f"{base_path}/candidates/{{candidate_id}}",
        operation_id=f"{operation_prefix}_recruitment_candidate",
    )
    def candidate(candidate_id: int):
        return _render(
            role=role,
            view="candidate",
            base_path=base_path,
            candidate_id=candidate_id,
        )

    app.include_router(router)


def register_recruitment_page_routes(app) -> None:
    _register_role_routes(
        app,
        role="hr_manager",
        base_path="/hr-manager",
        operation_prefix="hr_manager",
        include_settings=True,
        include_trash=True,
        include_rejected=True,
    )
    _register_role_routes(
        app,
        role="ceo",
        base_path="/ceo/recruitment",
        operation_prefix="ceo",
    )
    _register_role_routes(
        app,
        role="academic_director",
        base_path="/academic-director/recruitment",
        operation_prefix="academic_director",
        root_view="decisions",
        include_decisions=True,
    )
    _register_role_routes(
        app,
        role="head_of_department",
        base_path="/head-of-departments/recruitment",
        operation_prefix="head_of_department",
    )


__all__ = ["register_recruitment_page_routes"]
