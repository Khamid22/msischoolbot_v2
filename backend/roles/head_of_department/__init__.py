"""Head of Department role compatibility exports."""


def register_head_of_department_page_routes(app):
    from backend.pages.head_of_department import register_head_of_department_page_routes as register_routes

    return register_routes(app)

__all__ = ["register_head_of_department_page_routes"]
