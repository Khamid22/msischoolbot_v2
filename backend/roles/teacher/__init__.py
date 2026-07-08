"""Teacher role compatibility exports."""


def register_teacher_page_routes(app):
    from backend.pages.teacher import register_teacher_page_routes as register_routes

    return register_routes(app)

__all__ = ["register_teacher_page_routes"]
