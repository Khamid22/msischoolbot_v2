"""render_react_page contract and the hand-maintained url_for map."""

from fastapi.responses import HTMLResponse

from backend.core.web.rendering import render_react_page, _safe_json
from backend.modules.identity.session import url_for


def test_render_react_page_returns_html_response_with_status():
    response = render_react_page("login", {"a": 1}, title="T", status_code=404)
    assert isinstance(response, HTMLResponse)
    assert response.status_code == 404
    body = response.body.decode("utf-8")
    assert 'data-react-page="login"' in body
    assert "msi-react-bootstrap" in body


def test_props_json_is_html_safe():
    payload = _safe_json("page", {"x": "</script><b>&"})
    assert "</script>" not in payload
    assert "\\u003c" in payload and "\\u0026" in payload


def test_url_for_dashboard_routes():
    assert url_for("student.dashboard", student_id=5) == "/dashboard/5"
    assert (
        url_for("student.rating_board", student_id=5, subject="Math", school="school5")
        == "/dashboard/5/rating-board?subject=Math&school=school5"
    )
    assert url_for("student.login") == "/login"
    assert url_for("student.home", panel="students") == "/?panel=students"
