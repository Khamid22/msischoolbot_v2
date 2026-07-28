"""Public admission page adapter."""

from fastapi import APIRouter

from backend.core.web.rendering import render_react_page


def register_admission_page_routes(app) -> None:
    router = APIRouter()

    @router.get(
        "/admissions/{access_token}",
        operation_id="public_admission_page",
    )
    def public_admission_page(access_token: str):
        return render_react_page(
            "public-admission",
            {"accessToken": access_token},
            title="MSI School Admission",
            description="Review your contract and first invoice.",
            telegram=False,
        )

    app.include_router(router)


__all__ = ["register_admission_page_routes"]
