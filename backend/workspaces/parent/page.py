"""Parent portal page renderer + invite-link flow."""

import html

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from backend.core.guards import require_role
from backend.core.web_responses import redirect
from backend.core.request_context import session, request as ctx_request
from backend.core.rendering import generate_csrf

from backend.modules.communications.announcements_service import list_announcements
from backend.modules.learning_resources.service import list_resources
from backend.core.rendering import render_react_page
from backend.modules.parent_access.service import (
    claim_parent_invite_code,
    list_parent_client_children,
    list_parent_children,
    load_parent_invite_code_payload,
    parent_can_access_student,
    resolve_parent_child_dashboard,
)
from backend.modules.parent_access.cards import build_parent_workspace_cards
from backend.integrations.telegram.init_data import telegram_user_from_init_data
from backend.core.session import set_account_session, url_for


def _page(title, body_html, status_code=200, lang="uz", telegram_webapp=False):
    active_lang = "ru" if str(lang or "").lower() == "ru" else "uz"
    telegram_script = (
        '<script src="https://telegram.org/js/telegram-web-app.js"></script>'
        if telegram_webapp
        else ""
    )
    return HTMLResponse(
        f"""<!doctype html>
<html lang="{active_lang}" data-lang="{active_lang}">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{html.escape(title)}</title>
    {telegram_script}
    <style>
      .lang-toggle {{
        display:inline-flex; gap:4px; padding:4px; border:1px solid #dbe1ea;
        border-radius:999px; background:#f8fafc;
      }}
      .lang-button {{
        border:0; border-radius:999px; background:transparent; padding:7px 12px;
        font-size:13px; font-weight:800; color:#64748b; cursor:pointer;
      }}
      html[data-lang="uz"] .lang-button[data-lang-button="uz"],
      html[data-lang="ru"] .lang-button[data-lang-button="ru"] {{
        background:#2563eb; color:white; box-shadow:0 6px 16px rgba(37,99,235,.22);
      }}
      html[data-lang="uz"] [data-lang="ru"],
      html[data-lang="ru"] [data-lang="uz"] {{ display:none !important; }}
    </style>
  </head>
  <body style="font-family:system-ui,-apple-system,sans-serif;background:#f5f7fb;margin:0;padding:24px;color:#111827">
    <main style="max-width:560px;margin:8vh auto;background:white;border:1px solid #e5e7eb;border-radius:18px;padding:24px;box-shadow:0 12px 35px rgba(15,23,42,.08)">
      {body_html}
    </main>
    <script>
      (function() {{
        var root = document.documentElement;
        var initial = {active_lang!r};
        var stored = "";
        try {{ stored = window.localStorage.getItem("msi_parent_link_lang") || ""; }} catch (err) {{}}
        var current = stored === "ru" || stored === "uz" ? stored : initial;
        function apply(lang) {{
          current = lang === "ru" ? "ru" : "uz";
          root.setAttribute("data-lang", current);
          root.setAttribute("lang", current);
          try {{ window.localStorage.setItem("msi_parent_link_lang", current); }} catch (err) {{}}
          document.querySelectorAll("input[name='lang']").forEach(function(input) {{ input.value = current; }});
          document.querySelectorAll("[data-lang-button]").forEach(function(button) {{
            button.setAttribute("aria-pressed", button.getAttribute("data-lang-button") === current ? "true" : "false");
          }});
          document.querySelectorAll("[data-placeholder-uz]").forEach(function(input) {{
            input.setAttribute("placeholder", input.getAttribute("data-placeholder-" + current) || "");
          }});
        }}
        document.querySelectorAll("[data-lang-button]").forEach(function(button) {{
          button.addEventListener("click", function() {{ apply(button.getAttribute("data-lang-button")); }});
        }});
        apply(current);
      }})();
    </script>
  </body>
</html>""",
        status_code=status_code,
    )


def _invalid_link_page():
    return _page(
        "Havola yaroqsiz",
        """
        <h1 style="font-size:24px;margin:0 0 12px">
          <span data-lang="uz">Havola yaroqsiz</span>
          <span data-lang="ru">Ссылка недействительна</span>
        </h1>
        <p style="font-size:16px;line-height:1.5;color:#4b5563">
          <span data-lang="uz">Iltimos, administratordan yangi havola so'rang.</span>
          <span data-lang="ru">Пожалуйста, попросите администратора отправить новую ссылку.</span>
        </p>
        """,
        status_code=400,
    )


def _language_toggle(lang):
    return f"""
    <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0 0 18px">
      <p style="margin:0;font-size:13px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:#2563eb">MSI School</p>
      <div class="lang-toggle" aria-label="Language">
        <button class="lang-button" type="button" data-lang-button="uz" aria-pressed="{'true' if lang == 'uz' else 'false'}">UZ</button>
        <button class="lang-button" type="button" data-lang-button="ru" aria-pressed="{'true' if lang == 'ru' else 'false'}">RU</button>
      </div>
    </div>
    """


def _student_card(student_name, student_code):
    code_line = (
        f'<p style="margin:4px 0 0;color:#6b7280;font-size:14px">{html.escape(student_code)}</p>'
        if student_code
        else ""
    )
    return f"""
    <section style="border:1px solid #e5e7eb;border-radius:14px;background:#f9fafb;padding:16px;margin-bottom:18px">
      <p style="margin:0 0 4px;color:#6b7280;font-size:13px">
        <span data-lang="uz">O'quvchi</span>
        <span data-lang="ru">Ученик</span>
      </p>
      <p style="margin:0;font-size:20px;font-weight:800">{html.escape(student_name)}</p>
      {code_line}
    </section>
    """


def _field(label_uz, label_ru, name, value, *, input_type="text", placeholder_uz="", placeholder_ru=""):
    return f"""
    <label style="display:block;margin-bottom:14px">
      <span style="display:block;margin-bottom:6px;font-size:13px;font-weight:600;color:#374151">
        <span data-lang="uz">{html.escape(label_uz)}</span>
        <span data-lang="ru">{html.escape(label_ru)}</span>
      </span>
      <input name="{html.escape(name)}" type="{input_type}" value="{html.escape(value)}"
             data-placeholder-uz="{html.escape(placeholder_uz)}"
             data-placeholder-ru="{html.escape(placeholder_ru)}"
             placeholder="{html.escape(placeholder_uz)}" autocomplete="off"
             style="width:100%;box-sizing:border-box;border:1px solid #d1d5db;border-radius:10px;padding:11px 12px;font-size:16px;outline:none">
    </label>
    """


def _error_message(error_key):
    messages = {
        "full_name": ("Iltimos, to'liq ismni kiriting.", "Укажите полное имя."),
        "phone": ("Iltimos, telefon raqamini kiriting.", "Укажите номер телефона."),
        "telegram": (
            "Telegram orqali tasdiqlash amalga oshmadi. Havolani Telegram ichidan qayta oching.",
            "Не удалось подтвердить Telegram. Откройте ссылку внутри Telegram ещё раз.",
        ),
        "technical": ("Texnik xatolik. Birozdan so'ng qayta urinib ko'ring.", "Техническая ошибка. Попробуйте ещё раз."),
    }
    return messages.get(error_key or "", ("", ""))


def _telegram_connect_page(code, student_name, student_code, *, error_key="", lang="uz"):
    active_lang = "ru" if str(lang or "").lower() == "ru" else "uz"
    error_uz, error_ru = _error_message(error_key)
    error_html = (
        f'<p style="margin:0 0 14px;padding:10px 12px;border-radius:10px;background:#fef2f2;'
        f'border:1px solid #fecaca;color:#b91c1c;font-size:14px">'
        f'<span data-lang="uz">{html.escape(error_uz)}</span>'
        f'<span data-lang="ru">{html.escape(error_ru)}</span>'
        f'</p>'
        if error_key
        else ""
    )
    body = f"""
    {_language_toggle(active_lang)}
    <h1 style="font-size:26px;margin:0 0 12px">
      <span data-lang="uz">Telegram orqali ulanish</span>
      <span data-lang="ru">Подключение через Telegram</span>
    </h1>
    <p style="font-size:16px;line-height:1.5;color:#4b5563;margin:0 0 16px">
      <span data-lang="uz">Shaxsingiz Telegram orqali avtomatik tasdiqlanadi. Ma'lumot kiritish shart emas.</span>
      <span data-lang="ru">Ваш профиль Telegram будет подтверждён автоматически. Заполнять форму не нужно.</span>
    </p>
    {_student_card(student_name, student_code)}
    {error_html}
    <div id="tg-status" style="border:1px solid #dbeafe;border-radius:14px;background:#eff6ff;padding:14px 16px;color:#1e40af;font-size:15px;line-height:1.45">
      <strong>
        <span data-lang="uz">Ulanmoqda...</span>
        <span data-lang="ru">Подключаем...</span>
      </strong>
      <div style="margin-top:4px;color:#475569">
        <span data-lang="uz">Telegram oynasini yopmang.</span>
        <span data-lang="ru">Не закрывайте окно Telegram.</span>
      </div>
    </div>
    <div id="tg-fallback" style="display:none;margin-top:14px;border:1px solid #fed7aa;border-radius:14px;background:#fff7ed;padding:14px 16px;color:#9a3412;font-size:15px;line-height:1.45">
      <strong>
        <span data-lang="uz">Telegram Mini App kerak</span>
        <span data-lang="ru">Нужен Telegram Mini App</span>
      </strong>
      <div style="margin-top:4px">
        <span data-lang="uz">Bu havolani Telegram bot ichidagi tugma orqali oching. Oddiy brauzer ota-onani avtomatik aniqlay olmaydi.</span>
        <span data-lang="ru">Откройте ссылку через кнопку внутри Telegram-бота. Обычный браузер не может автоматически определить родителя.</span>
      </div>
    </div>
    <form id="tg-claim-form" method="post" action="/parent/invite/{html.escape(code)}" style="display:none">
      <input type="hidden" name="lang" value="{html.escape(active_lang)}">
      <input id="tg-init-data" type="hidden" name="init_data" value="">
    </form>
    <script>
      (function() {{
        var attempts = 0;
        var maxAttempts = 20;
        var form = document.getElementById("tg-claim-form");
        var input = document.getElementById("tg-init-data");
        var fallback = document.getElementById("tg-fallback");
        var status = document.getElementById("tg-status");

        function showFallback() {{
          if (fallback) fallback.style.display = "block";
          if (status) {{
            status.style.borderColor = "#fed7aa";
            status.style.background = "#fff7ed";
            status.style.color = "#9a3412";
            status.innerHTML =
              '<strong><span data-lang="uz">Avtomatik ulanish topilmadi</span><span data-lang="ru">Автоподключение недоступно</span></strong>';
          }}
        }}

        function trySubmit() {{
          attempts += 1;
          var tg = window.Telegram && window.Telegram.WebApp;
          if (tg && tg.initData) {{
            try {{
              tg.ready();
              tg.expand();
            }} catch (err) {{}}
            input.value = tg.initData;
            form.submit();
            return;
          }}
          if (attempts >= maxAttempts) {{
            showFallback();
            return;
          }}
          window.setTimeout(trySubmit, 100);
        }}

        if (document.readyState === "loading") {{
          document.addEventListener("DOMContentLoaded", trySubmit);
        }} else {{
          trySubmit();
        }}
      }})();
    </script>
    """
    return _page(
        "Telegram orqali ulanish",
        body,
        lang=active_lang,
        telegram_webapp=True,
    )


def _invite_form_page(code, student_name, student_code, *, error_key="", values=None):
    values = values or {}
    lang = "ru" if str(values.get("lang") or "").lower() == "ru" else "uz"
    error_uz, error_ru = _error_message(error_key)
    error_html = (
        f'<p style="margin:0 0 14px;padding:10px 12px;border-radius:10px;background:#fef2f2;'
        f'border:1px solid #fecaca;color:#b91c1c;font-size:14px">'
        f'<span data-lang="uz">{html.escape(error_uz)}</span>'
        f'<span data-lang="ru">{html.escape(error_ru)}</span>'
        f'</p>'
        if error_key
        else ""
    )
    body = f"""
    {_language_toggle(lang)}
    <h1 style="font-size:26px;margin:0 0 12px">
      <span data-lang="uz">Ota-ona ulanishi</span>
      <span data-lang="ru">Подключение родителя</span>
    </h1>
    <p style="font-size:16px;line-height:1.5;color:#4b5563;margin:0 0 16px">
      <span data-lang="uz">Farzandingiz kabinetiga ulanish uchun ma'lumotlaringizni kiriting.</span>
      <span data-lang="ru">Заполните данные, чтобы подключиться к кабинету ученика.</span>
    </p>
    {_student_card(student_name, student_code)}
    {error_html}
    <form method="post" action="/parent/invite/{html.escape(code)}">
      <input type="hidden" name="lang" value="{html.escape(lang)}">
      {_field("To'liq ism", "Полное имя", "full_name", values.get("full_name", ""), placeholder_uz="Familiya Ism", placeholder_ru="Фамилия Имя")}
      {_field("Telefon raqami", "Номер телефона", "phone", values.get("phone", ""), input_type="tel", placeholder_uz="+998 90 123 45 67", placeholder_ru="+998 90 123 45 67")}
      {_field("Telegram username", "Telegram username", "telegram_username", values.get("telegram_username", ""), placeholder_uz="@username", placeholder_ru="@username")}
      <button type="submit"
              style="width:100%;border:0;border-radius:12px;padding:13px;font-size:16px;font-weight:700;color:white;background:#2563eb;cursor:pointer">
        <span data-lang="uz">Ulanish</span>
        <span data-lang="ru">Подключиться</span>
      </button>
    </form>
    """
    return _page("Ota-ona ulanishi", body, lang=lang)


def _confirmation_page(student_name, student_code, parent, *, lang="uz"):
    parent_name = html.escape(str((parent or {}).get("full_name") or "").strip())
    greeting_uz = f"<b>{parent_name}</b>, " if parent_name else ""
    greeting_ru = f"<b>{parent_name}</b>, " if parent_name else ""
    return _page(
        "Ulandingiz",
        f"""
        {_language_toggle('ru' if str(lang or '').lower() == 'ru' else 'uz')}
        <h1 style="font-size:26px;margin:0 0 12px">
          <span data-lang="uz">Ulandingiz ✓</span>
          <span data-lang="ru">Вы подключены ✓</span>
        </h1>
        <p style="font-size:16px;line-height:1.5;color:#4b5563;margin:0 0 16px">
          <span data-lang="uz">{greeting_uz}siz quyidagi o'quvchiga muvaffaqiyatli ulandingiz.</span>
          <span data-lang="ru">{greeting_ru}вы успешно подключены к ученику.</span>
        </p>
        {_student_card(student_name, student_code)}
        <p style="font-size:14px;line-height:1.5;color:#6b7280;margin:0">
          <span data-lang="uz">Administrator tez orada siz bilan bog'lanadi.</span>
          <span data-lang="ru">Администратор скоро свяжется с вами.</span>
        </p>
        """,
        lang=lang,
    )


def _telegram_parent_from_init_data(init_data):
    user = telegram_user_from_init_data(init_data)
    if not user:
        return None

    first_name = str(user.get("first_name") or "").strip()
    last_name = str(user.get("last_name") or "").strip()
    username = str(user.get("username") or "").strip().lstrip("@")
    full_name = " ".join(part for part in (first_name, last_name) if part).strip()
    if not full_name:
        full_name = f"Telegram parent {int(user['id'])}"

    return {
        "telegram_user_id": int(user["id"]),
        "full_name": full_name,
        "phone": "",
        "telegram_username": username,
    }


def register_parent_invite_routes(app):
    @app.get("/parent/invite/{code}")
    def parent_invite_code_link(code: str):
        payload = load_parent_invite_code_payload(code)
        if not payload:
            return _invalid_link_page()
        student_name = str(payload.get("student_name") or "Student").strip()
        student_code = str(payload.get("student_code") or "").strip()
        lang = str(ctx_request.args.get("lang") or "uz").strip().lower()
        if str(ctx_request.args.get("manual") or "").strip() == "1":
            return _invite_form_page(code, student_name, student_code, values={"lang": lang})
        return _telegram_connect_page(code, student_name, student_code, lang=lang)

    @app.post("/parent/invite/{code}")
    def parent_invite_submit(code: str):
        payload = load_parent_invite_code_payload(code)
        if not payload:
            return _invalid_link_page()

        student_name = str(payload.get("student_name") or "Student").strip()
        student_code = str(payload.get("student_code") or "").strip()
        student_row_id = int(payload.get("student_row_id") or 0)

        # RequestContextMiddleware already parsed the body into request.state;
        # read it via the Flask-style proxy (re-reading the ASGI body here would
        # hang, since the stream is already consumed).
        form = ctx_request.form
        lang = str(form.get("lang") or "uz").strip().lower()
        init_data = str(form.get("init_data") or "").strip()
        if init_data:
            telegram_parent = _telegram_parent_from_init_data(init_data)
            if not telegram_parent:
                return _telegram_connect_page(
                    code,
                    student_name,
                    student_code,
                    error_key="telegram",
                    lang=lang,
                )
            if not student_row_id:
                return _invalid_link_page()
            try:
                parent = claim_parent_invite_code(
                    code,
                    full_name=telegram_parent["full_name"],
                    phone=telegram_parent["phone"],
                    telegram_username=telegram_parent["telegram_username"],
                    telegram_user_id=telegram_parent["telegram_user_id"],
                )
            except Exception:
                return _telegram_connect_page(
                    code,
                    student_name,
                    student_code,
                    error_key="technical",
                    lang=lang,
                )
            if not parent:
                return _invalid_link_page()

            if not set_account_session(parent.get("auth_result")):
                return _telegram_connect_page(
                    code,
                    student_name,
                    student_code,
                    error_key="technical",
                    lang=lang,
                )
            return redirect("/")

        values = {
            "full_name": str(form.get("full_name") or "").strip(),
            "phone": str(form.get("phone") or "").strip(),
            "telegram_username": str(form.get("telegram_username") or "").strip(),
            "lang": lang,
        }

        if not values["full_name"]:
            return _invite_form_page(
                code, student_name, student_code,
                error_key="full_name", values=values,
            )
        if not values["phone"]:
            return _invite_form_page(
                code, student_name, student_code,
                error_key="phone", values=values,
            )
        if not student_row_id:
            return _invalid_link_page()

        try:
            parent = claim_parent_invite_code(
                code,
                full_name=values["full_name"],
                phone=values["phone"],
                telegram_username=values["telegram_username"],
                telegram_user_id=None,
            )
        except Exception:
            return _invite_form_page(
                code, student_name, student_code,
                error_key="technical",
                values=values,
            )
        if not parent:
            return _invalid_link_page()

        if not set_account_session(parent.get("auth_result")):
            return _invite_form_page(
                code, student_name, student_code,
                error_key="technical", values=values,
            )
        return redirect("/")

    @app.get("/parent/dashboard/{student_row_id}")
    def parent_child_dashboard(student_row_id: int):
        try:
            parent_id = int(session.get("parent_id", 0) or 0)
        except (TypeError, ValueError):
            parent_id = 0
        if parent_id <= 0:
            return redirect("/")

        if not parent_can_access_student(parent_id, student_row_id):
            return _page(
                "Access denied",
                """
                <h1>Access denied</h1>
                <p>This student is not linked to your parent account.</p>
                <p><a href="/">Return to parent portal</a></p>
                """,
                status_code=403,
            )

        resolved = resolve_parent_child_dashboard(student_row_id)
        if not resolved:
            return _page(
                "Dashboard unavailable",
                """
                <h1>Dashboard unavailable</h1>
                <p>No dashboard data was found for this student.</p>
                <p><a href="/">Return to parent portal</a></p>
                """,
                status_code=404,
            )

        return redirect(
            url_for(
                "student.dashboard",
                student_id=int(resolved["student_id"]),
                subject=resolved.get("subject", ""),
                group=resolved.get("group", ""),
                school=resolved.get("school", ""),
                parent_return="1",
            )
        )


def build_render_parent_page():
    def render_parent_page():
        try:
            parent_id = int(session.get("parent_id", 0) or 0)
            admin_id = int(session.get("admin_id", 0) or 0)
        except (TypeError, ValueError):
            parent_id = 0
            admin_id = 0

        children = []
        children_for_cards = None
        try:
            children = list_parent_client_children(parent_id) if parent_id else []
            if not children and admin_id:
                children = list_parent_children(admin_id)
            children_for_cards = children
        except Exception:
            children = []
        workspace_cards = build_parent_workspace_cards(
            parent_id=parent_id,
            children=children_for_cards,
        )

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
                "workspaceCards": workspace_cards,
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


def register_parent_page_routes(app):
    router = APIRouter(dependencies=[Depends(require_role("parent"))])
    render_parent_page = build_render_parent_page()

    @router.get("/parent")
    def parent_home():
        return render_parent_page()

    app.include_router(router)


__all__ = [
    "build_render_parent_page",
    "register_parent_invite_routes",
    "register_parent_page_routes",
]
