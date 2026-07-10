"""
Core React page rendering boundary.
-----------------
Generates HTML pages directly from Python — no Jinja2 templates needed.

How it works
------------
  1. A backend route builds a props dict (camelCase keys matching React component props).
  2. The route calls render_react_page("page-name", props, title="...").
  3. render_react_page() returns an HTML string with the props embedded as JSON.
  4. The browser loads React, which reads the JSON and renders the right page.

The page name must match a key in frontend/src/App.tsx's pageMap.
"""

import json
import os
import re
import threading
from typing import Any

from fastapi.responses import HTMLResponse
from markupsafe import escape

ASSET_VERSION = "1"
STATIC_FOLDER = ""


def url_for(endpoint: str, **kwargs) -> str:
    if endpoint == "static":
        filename = kwargs.get("filename", "")
        v = kwargs.get("v")
        url = f"/static/{filename}"
        if v:
            url += f"?v={v}"
        return url
    if endpoint == "system.manifest":
        return "/manifest.webmanifest"
    raise ValueError(f"Unknown endpoint in render url_for: {endpoint}")



# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_MANIFEST_CACHE_LOCK = threading.Lock()
_MANIFEST_CACHE_PATH = ""
_MANIFEST_CACHE_MTIME_NS = -1
_MANIFEST_CACHE_DATA: dict[str, Any] | None = None

_TG_SAFE_AREA_PRIME_SCRIPT = """
    <script>
      (function () {
        var docEl = document.documentElement;
        if (!docEl || typeof window.getComputedStyle !== "function") {
          return;
        }
        var style = docEl.style;
        var computed = getComputedStyle(docEl);
        var vars = [
          "--tg-safe-area-inset-top",
          "--tg-safe-area-inset-bottom",
          "--tg-content-safe-area-inset-top",
          "--tg-content-safe-area-inset-bottom",
          "--tg-safe-area-inset-left",
          "--tg-safe-area-inset-right"
        ];
        for (var i = 0; i < vars.length; i += 1) {
          var name = vars[i];
          var value = String(computed.getPropertyValue(name) || "").trim();
          if (value && value !== "0px") {
            style.setProperty(name, value);
          }
        }
      })();
    </script>
""".rstrip()

_MINIMAL_CRITICAL_CSS = """
    <style>
      :root { --msi-critical-bg: hsl(0 0% 97%); }
      *, *::before, *::after { box-sizing: border-box; }
      html, body, #root {
        margin: 0;
        min-height: 100dvh;
        background: var(--msi-critical-bg);
      }
      body {
        font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
        -webkit-font-smoothing: antialiased;
      }
    </style>
""".rstrip()

def _asset_version() -> str:
    """Cache-busting version string, set once at startup."""
    return str(ASSET_VERSION)


def _react_manifest_path() -> str:
    static_root = STATIC_FOLDER or ""
    return os.path.join(static_root, "react", "manifest.json")



def clear_react_manifest_cache() -> None:
    global _MANIFEST_CACHE_PATH, _MANIFEST_CACHE_MTIME_NS, _MANIFEST_CACHE_DATA
    with _MANIFEST_CACHE_LOCK:
        _MANIFEST_CACHE_PATH = ""
        _MANIFEST_CACHE_MTIME_NS = -1
        _MANIFEST_CACHE_DATA = None


def _load_react_manifest() -> dict[str, Any]:
    path = _react_manifest_path()
    global _MANIFEST_CACHE_PATH, _MANIFEST_CACHE_MTIME_NS, _MANIFEST_CACHE_DATA
    try:
        stat_result = os.stat(path)
        mtime_ns = int(getattr(stat_result, "st_mtime_ns", int(stat_result.st_mtime * 1_000_000_000)))
    except OSError:
        return {}

    with _MANIFEST_CACHE_LOCK:
        if (
            _MANIFEST_CACHE_DATA is not None
            and _MANIFEST_CACHE_PATH == path
            and _MANIFEST_CACHE_MTIME_NS == mtime_ns
        ):
            return _MANIFEST_CACHE_DATA

        try:
            with open(path, "r", encoding="utf-8") as manifest_file:
                data = json.load(manifest_file)
        except (OSError, json.JSONDecodeError):
            return {}

        manifest = data if isinstance(data, dict) else {}
        _MANIFEST_CACHE_PATH = path
        _MANIFEST_CACHE_MTIME_NS = mtime_ns
        _MANIFEST_CACHE_DATA = manifest
        return manifest


def _resolve_react_assets() -> tuple[str, str]:
    manifest = _load_react_manifest()

    entry = manifest.get("index.html") if isinstance(manifest, dict) else None
    js_file = ""
    css_file = ""

    if isinstance(entry, dict):
        js_file = str(entry.get("file") or "").strip()
        css_files = entry.get("css")
        if isinstance(css_files, list) and css_files:
            css_file = str(css_files[0] or "").strip()

    # Newer Vite manifests may emit CSS as a standalone "style.css" entry
    # instead of listing it under index.html->css.
    if not css_file and isinstance(manifest, dict):
        style_entry = manifest.get("style.css")
        if isinstance(style_entry, dict):
            css_file = str(style_entry.get("file") or "").strip()

    if js_file:
        return js_file, css_file

    return "app.js", "app.css"


def _resolve_react_preloads() -> tuple[str, ...]:
    """Return static-import chunk files of the entry, for <link rel=modulepreload>.

    Without these hints the browser discovers vendor chunks only after the
    entry module is downloaded and parsed, adding a network round trip.
    """
    manifest = _load_react_manifest()
    if not isinstance(manifest, dict):
        return ()

    preload_files: list[str] = []
    seen_keys = {"index.html"}

    def walk(key: str) -> None:
        node = manifest.get(key)
        if not isinstance(node, dict):
            return
        imports = node.get("imports")
        if not isinstance(imports, list):
            return
        for imported_key in imports:
            if not isinstance(imported_key, str) or imported_key in seen_keys:
                continue
            seen_keys.add(imported_key)
            child = manifest.get(imported_key)
            if isinstance(child, dict):
                child_file = str(child.get("file") or "").strip()
                if child_file:
                    preload_files.append(child_file)
            walk(imported_key)

    walk("index.html")
    return tuple(preload_files)


def _is_hashed_asset(file_name: str) -> bool:
    return bool(re.search(r"-[A-Za-z0-9_-]{8,}\.", str(file_name)))


def _react_asset_url(file_name: str, version: str) -> str:
    if _is_hashed_asset(file_name):
        return url_for("static", filename=f"react/{file_name}")
    return url_for("static", filename=f"react/{file_name}", v=version)


def _safe_json(page_name: str, props: dict) -> str:
    """Serialize page + props to HTML-safe JSON.

    Escapes <, >, and & so the JSON can safely sit inside a
    <script type="application/json"> tag without breaking the HTML parser.
    """
    raw = json.dumps(
        {"page": page_name, "props": props},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return raw.replace("<", r"\u003c").replace(">", r"\u003e").replace("&", r"\u0026")


# ---------------------------------------------------------------------------
# Public render functions
# ---------------------------------------------------------------------------

def render_react_page(
    page_name: str,
    props: dict,
    *,
    title: str = "MSI School Portal",
    description: str = "MSI School Portal",
    telegram: bool = True,
    back_mode: str | None = None,
    back_url: str | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    """Return an HTMLResponse that boots the React app for the given page.

    Args:
        page_name:   React page key (e.g. "student-dashboard"). Must match a
                     key in frontend/src/App.tsx's pageMap.
        props:       camelCase props passed straight to the React page component.
        title:       Browser tab title.
        description: <meta name="description"> content.
        telegram:    Whether to load the Telegram WebApp JS bridge.
        back_mode:   Telegram back button mode ("history" or None).
        back_url:    URL the Telegram back button navigates to.
        status_code: HTTP status for the response (e.g. 404 for not-found pages).
    """
    v = _asset_version()
    props_json = _safe_json(page_name, props)
    title_safe = str(escape(title))
    desc_safe = str(escape(description))

    favicon_url = url_for("static", filename="images/favicon.png")
    manifest_url = url_for("system.manifest")
    js_file, css_file = _resolve_react_assets()
    css_url = _react_asset_url(css_file, v) if css_file else ""
    js_url = _react_asset_url(js_file, v)
    preload_links = "".join(
        f'\n    <link rel="modulepreload" href="{_react_asset_url(preload_file, v)}" />'
        for preload_file in _resolve_react_preloads()
    )
    tg_bundle_url = url_for("static", filename="js/bundles/telegram-base.js", v=v)

    tg_head = (
        '\n    <link rel="dns-prefetch" href="//telegram.org" />'
        '\n    <link rel="preconnect" href="https://telegram.org" crossorigin />'
        '\n    <script defer src="https://telegram.org/js/telegram-web-app.js"></script>'
        f"\n{_TG_SAFE_AREA_PRIME_SCRIPT}"
    ) if telegram else ""

    tg_script = f'\n    <script defer src="{tg_bundle_url}"></script>' if telegram else ""

    body_attrs = f' data-react-page="{str(escape(page_name))}"'
    if back_mode:
        body_attrs += f' data-tg-back-mode="{str(escape(back_mode))}"'
    if back_url:
        body_attrs += f' data-tg-back-url="{str(escape(back_url))}"'

    html = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
    <meta name="theme-color" content="#0a0a0a" />
    <meta name="mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
    <meta name="format-detection" content="telephone=no" />
    <meta name="description" content="{desc_safe}" />{tg_head}
    <title>{title_safe}</title>
{_MINIMAL_CRITICAL_CSS}
    <link rel="icon" type="image/png" href="{favicon_url}" />
    <link rel="manifest" href="{manifest_url}" />
    {"<link rel=\"stylesheet\" href=\"" + css_url + "\" />" if css_url else ""}{preload_links}
  </head>
  <body{body_attrs}>
    <div id="root"></div>
    <script id="msi-react-bootstrap" type="application/json">{props_json}</script>{tg_script}
    <script type="module" src="{js_url}"></script>
  </body>
</html>"""
    return HTMLResponse(html, status_code=status_code)


def render_admin_redirect(redirect_url: str) -> HTMLResponse:
    """Return the standalone HTML page shown to admins inside the Telegram mini app.

    This page has no React — it simply tells the admin to open the website,
    and auto-calls Telegram.WebApp.openLink() to do it.
    """
    url_json = json.dumps(str(redirect_url))
    favicon_url = url_for("static", filename="images/favicon.png")

    html = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
    <meta name="theme-color" content="#0a0a0a" />
    <title>Open Admin Website</title>
    <link rel="icon" type="image/png" href="{favicon_url}" />
    <script defer src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
      :root {{
        color-scheme: light;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: #f5f5f5;
        color: #0a0a0a;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        min-height: 100dvh;
        display: flex;
        align-items: center;
        justify-content: center;
        padding:
          max(24px, env(safe-area-inset-top, 0px))
          max(16px, env(safe-area-inset-right, 0px))
          max(24px, env(safe-area-inset-bottom, 0px))
          max(16px, env(safe-area-inset-left, 0px));
        background: radial-gradient(circle at top, rgba(0,0,0,.05), transparent 45%), #f5f5f5;
      }}
      .card {{
        width: min(100%, 420px);
        border-radius: 28px;
        background: #fff;
        box-shadow: 0 1px 3px rgba(0,0,0,.08), 0 0 0 1px rgba(0,0,0,.04);
        padding: 28px 24px;
      }}
      h1 {{ margin: 0 0 10px; font-size: 1.4rem; line-height: 1.2; }}
      p {{ margin: 0; color: rgba(10,10,10,.66); line-height: 1.6; }}
      .actions {{ display: flex; flex-direction: column; gap: 12px; margin-top: 24px; }}
      .button {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 52px;
        border-radius: 16px;
        border: 0;
        background: #0a0a0a;
        color: #f5f5f5;
        font: inherit;
        font-weight: 700;
        text-decoration: none;
        cursor: pointer;
      }}
      .secondary {{ background: rgba(0,0,0,.06); color: #0a0a0a; }}
    </style>
  </head>
  <body>
    <div class="card">
      <h1>Admin access continues on the website</h1>
      <p>Your credentials were accepted. Open the website to continue in the admin panel outside the Telegram Mini App.</p>
      <div class="actions">
        <a id="openAdminWebsite" class="button" href="{str(escape(redirect_url))}" target="_blank" rel="noopener noreferrer">
          Open Admin Website
        </a>
        <button id="retryOpenAdminWebsite" type="button" class="button secondary">Try Again</button>
      </div>
    </div>
    <script>
      (function () {{
        var targetUrl = {url_json};
        function openAdminWebsite() {{
          var webApp = window.Telegram && window.Telegram.WebApp;
          if (webApp && typeof webApp.ready === "function") {{
            try {{ webApp.ready(); }} catch (_) {{}}
          }}
          if (webApp && typeof webApp.openLink === "function") {{
            try {{
              webApp.openLink(targetUrl);
              if (typeof webApp.close === "function") {{
                window.setTimeout(function () {{ try {{ webApp.close(); }} catch (_) {{}} }}, 160);
              }}
              return;
            }} catch (_) {{}}
          }}
          window.open(targetUrl, "_blank", "noopener,noreferrer");
        }}
        var primary = document.getElementById("openAdminWebsite");
        var retry = document.getElementById("retryOpenAdminWebsite");
        if (primary) primary.addEventListener("click", function (e) {{ e.preventDefault(); openAdminWebsite(); }});
        if (retry) retry.addEventListener("click", openAdminWebsite);
        window.setTimeout(openAdminWebsite, 80);
    </script>
  </body>
</html>"""
    return HTMLResponse(html)


def generate_csrf() -> str:
    import secrets
    from backend.core.request_context import get_current_request
    request = get_current_request()
    if request is None:
        return ""
    # We use a signed session cookie. Store token in session if not present.
    if "csrf_token" not in request.session:
        request.session["csrf_token"] = secrets.token_hex(16)
    return request.session["csrf_token"]
