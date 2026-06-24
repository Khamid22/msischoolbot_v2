"""Parent portal page renderer + invite-link flow."""

import html
import os

from fastapi.responses import HTMLResponse
from itsdangerous import BadSignature, URLSafeTimedSerializer

from web.backend.utils.context import session, request as ctx_request
from web.backend.render import generate_csrf

from web.backend.domains.announcements.service import list_announcements
from web.backend.domains.resources.service import list_resources
from web.backend.render import render_react_page
from web.backend.roles.admin.services.parent_service import list_parent_children
from web.backend.roles.parent.services import link_parent_via_invite

_INVITE_MAX_AGE = 60 * 60 * 24 * 14  # 14 days


def _parent_invite_serializer():
    secret = os.environ.get("APP_SECRET_KEY", os.environ.get("FLASK_SECRET_KEY", "")).strip()
    if not secret:
        raise RuntimeError("APP_SECRET_KEY is required to read parent invite links.")
    return URLSafeTimedSerializer(secret_key=secret, salt="msi-parent-invite-v1")


def _load_invite_payload(token):
    """Return the signed invite payload, or None if the token is bad/expired."""
    try:
        return _parent_invite_serializer().loads(str(token or ""), max_age=_INVITE_MAX_AGE)
    except BadSignature:
        return None


def _page(title, body_html, status_code=200):
    return HTMLResponse(
        f"""<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{html.escape(title)}</title>
  </head>
  <body style="font-family:system-ui,-apple-system,sans-serif;background:#f5f7fb;margin:0;padding:24px;color:#111827">
    <main style="max-width:560px;margin:8vh auto;background:white;border:1px solid #e5e7eb;border-radius:18px;padding:24px;box-shadow:0 12px 35px rgba(15,23,42,.08)">
      {body_html}
    </main>
  </body>
</html>""",
        status_code=status_code,
    )


def _invalid_link_page():
    return _page(
        "Ссылка недействительна",
        """
        <h1 style="font-size:24px;margin:0 0 12px">Havola yaroqsiz / Ссылка недействительна</h1>
        <p style="font-size:16px;line-height:1.5;color:#4b5563">
          Iltimos, administratordan yangi havola so'rang. / Пожалуйста, попросите администратора отправить новую ссылку.
        </p>
        """,
        status_code=400,
    )


def _student_card(student_name, student_code):
    code_line = (
        f'<p style="margin:4px 0 0;color:#6b7280;font-size:14px">{html.escape(student_code)}</p>'
        if student_code
        else ""
    )
    return f"""
    <section style="border:1px solid #e5e7eb;border-radius:14px;background:#f9fafb;padding:16px;margin-bottom:18px">
      <p style="margin:0 0 4px;color:#6b7280;font-size:13px">O'quvchi / Ученик</p>
      <p style="margin:0;font-size:20px;font-weight:800">{html.escape(student_name)}</p>
      {code_line}
    </section>
    """


def _field(label, name, value, *, input_type="text", placeholder=""):
    return f"""
    <label style="display:block;margin-bottom:14px">
      <span style="display:block;margin-bottom:6px;font-size:13px;font-weight:600;color:#374151">{html.escape(label)}</span>
      <input name="{html.escape(name)}" type="{input_type}" value="{html.escape(value)}"
             placeholder="{html.escape(placeholder)}" autocomplete="off"
             style="width:100%;box-sizing:border-box;border:1px solid #d1d5db;border-radius:10px;padding:11px 12px;font-size:16px;outline:none">
    </label>
    """


def _invite_form_page(token, student_name, student_code, *, error="", values=None):
    values = values or {}
    error_html = (
        f'<p style="margin:0 0 14px;padding:10px 12px;border-radius:10px;background:#fef2f2;'
        f'border:1px solid #fecaca;color:#b91c1c;font-size:14px">{html.escape(error)}</p>'
        if error
        else ""
    )
    body = f"""
    <p style="margin:0 0 8px;font-size:13px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#2563eb">MSI School</p>
    <h1 style="font-size:26px;margin:0 0 12px">Ota-ona ulanishi / Подключение родителя</h1>
    <p style="font-size:16px;line-height:1.5;color:#4b5563;margin:0 0 16px">
      Farzandingiz kabinetiga ulanish uchun ma'lumotlaringizni kiriting. /
      Заполните данные, чтобы подключиться к кабинету ученика.
    </p>
    {_student_card(student_name, student_code)}
    {error_html}
    <form method="post" action="/parent/link/{html.escape(token)}">
      {_field("To'liq ism / Полное имя", "full_name", values.get("full_name", ""), placeholder="Familiya Ism")}
      {_field("Telefon raqami / Номер телефона", "phone", values.get("phone", ""), input_type="tel", placeholder="+998 90 123 45 67")}
      {_field("Telegram username", "telegram_username", values.get("telegram_username", ""), placeholder="@username")}
      <button type="submit"
              style="width:100%;border:0;border-radius:12px;padding:13px;font-size:16px;font-weight:700;color:white;background:#2563eb;cursor:pointer">
        Ulanish / Подключиться
      </button>
    </form>
    """
    return _page("Подключение родителя", body)


def _confirmation_page(student_name, student_code, parent):
    parent_name = html.escape(str((parent or {}).get("full_name") or "").strip())
    return _page(
        "Вы подключены",
        f"""
        <p style="margin:0 0 8px;font-size:13px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#16a34a">MSI School</p>
        <h1 style="font-size:26px;margin:0 0 12px">Ulandingiz / Вы подключены ✓</h1>
        <p style="font-size:16px;line-height:1.5;color:#4b5563;margin:0 0 16px">
          {('<b>' + parent_name + '</b>, ') if parent_name else ''}siz quyidagi o'quvchiga muvaffaqiyatli ulandingiz. /
          вы успешно подключены к ученику.
        </p>
        {_student_card(student_name, student_code)}
        <p style="font-size:14px;line-height:1.5;color:#6b7280;margin:0">
          Administrator tez orada siz bilan bog'lanadi. / Администратор скоро свяжется с вами.
        </p>
        """,
    )


def register_parent_invite_routes(app):
    @app.get("/parent/link/{token}")
    def parent_invite_link(token: str):
        payload = _load_invite_payload(token)
        if payload is None:
            return _invalid_link_page()
        student_name = str(payload.get("student_name") or "Student").strip()
        student_code = str(payload.get("student_code") or "").strip()
        return _invite_form_page(token, student_name, student_code)

    @app.post("/parent/link/{token}")
    def parent_invite_submit(token: str):
        payload = _load_invite_payload(token)
        if payload is None:
            return _invalid_link_page()

        student_name = str(payload.get("student_name") or "Student").strip()
        student_code = str(payload.get("student_code") or "").strip()
        student_row_id = int(payload.get("student_row_id") or 0)

        # RequestContextMiddleware already parsed the body into request.state;
        # read it via the Flask-style proxy (re-reading the ASGI body here would
        # hang, since the stream is already consumed).
        form = ctx_request.form
        values = {
            "full_name": str(form.get("full_name") or "").strip(),
            "phone": str(form.get("phone") or "").strip(),
            "telegram_username": str(form.get("telegram_username") or "").strip(),
        }

        if not values["full_name"]:
            return _invite_form_page(
                token, student_name, student_code,
                error="Iltimos, to'liq ismni kiriting. / Укажите полное имя.", values=values,
            )
        if not values["phone"]:
            return _invite_form_page(
                token, student_name, student_code,
                error="Iltimos, telefon raqamini kiriting. / Укажите номер телефона.", values=values,
            )
        if not student_row_id:
            return _invalid_link_page()

        try:
            parent = link_parent_via_invite(
                student_row_id,
                full_name=values["full_name"],
                phone=values["phone"],
                telegram_username=values["telegram_username"],
            )
        except Exception:
            return _invite_form_page(
                token, student_name, student_code,
                error="Texnik xatolik. Birozdan so'ng qayta urinib ko'ring. / Техническая ошибка. Попробуйте ещё раз.",
                values=values,
            )

        return _confirmation_page(student_name, student_code, parent)


def build_render_parent_page():
    def render_parent_page():
        try:
            admin_id = int(session.get("admin_id", 0) or 0)
        except (TypeError, ValueError):
            admin_id = 0

        children = list_parent_children(admin_id) if admin_id else []

        resources = []
        try:
            raw_resources = list_resources()
            resources = [dict(r) for r in raw_resources] if raw_resources else []
        except Exception:
            pass

        announcements = []
        try:
            raw_announcements = list_announcements()
            announcements = raw_announcements if raw_announcements else []
        except Exception:
            pass

        auth_login = str(session.get("auth_login", "")).strip()

        return render_react_page(
            "parent-home",
            {
                "authLogin": auth_login,
                "parentChildren": children,
                "resourcesList": resources,
                "adminAnnouncements": announcements,
                "currentSchool": "all",
                "csrfToken": generate_csrf(),
                "logoutUrl": "/logout",
            },
            title="Parent Portal",
            description="Track your children's academic progress.",
        )

    return render_parent_page


__all__ = ["build_render_parent_page", "register_parent_invite_routes"]
