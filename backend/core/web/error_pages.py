"""Dependency-free HTML error responses used when normal page rendering fails."""

from __future__ import annotations

from html import escape

from fastapi.responses import HTMLResponse


def internal_server_error_page(request_id: str) -> HTMLResponse:
    safe_request_id = escape(str(request_id or "unavailable"), quote=True)
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>MSI School · Something went wrong</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; padding: 24px; background: #f5f7fb; color: #111827; }}
    main {{ width: min(520px, 100%); border: 1px solid #e2e8f0; border-radius: 20px; background: white; padding: 32px; box-shadow: 0 18px 50px rgba(15, 23, 42, .09); }}
    .mark {{ display: grid; place-items: center; width: 44px; height: 44px; border-radius: 12px; background: #172554; color: white; font-weight: 800; }}
    h1 {{ margin: 22px 0 8px; font-size: 1.5rem; }}
    p {{ margin: 0; line-height: 1.6; color: #64748b; }}
    .request {{ margin-top: 20px; border-radius: 10px; background: #f1f5f9; padding: 12px; font: 600 .75rem ui-monospace, SFMono-Regular, Menlo, monospace; color: #475569; overflow-wrap: anywhere; }}
    a {{ display: inline-flex; margin-top: 22px; border-radius: 10px; background: #172554; padding: 11px 16px; color: white; font-weight: 700; text-decoration: none; }}
  </style>
</head>
<body>
  <main>
    <div class="mark" aria-hidden="true">M</div>
    <h1>We could not open this page</h1>
    <p>The error was recorded. Please try again; if it continues, send the request ID to the system administrator.</p>
    <div class="request">Request ID: {safe_request_id}</div>
    <a href="">Try again</a>
  </main>
</body>
</html>"""
    return HTMLResponse(
        html,
        status_code=500,
        headers={"Cache-Control": "no-store, max-age=0"},
    )


__all__ = ["internal_server_error_page"]
