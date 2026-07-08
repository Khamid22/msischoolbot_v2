"""Academic Director role compatibility exports."""


def register_academic_director_page_routes(app):
    from backend.pages.academic_director import register_academic_director_page_routes as register_routes

    return register_routes(app)

__all__ = ["register_academic_director_page_routes"]
