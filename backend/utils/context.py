import contextvars
import json
import os
import shutil
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import UploadFile


_request_context = contextvars.ContextVar("request_context")


class RequestContextMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        cached_body = None
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            content_type = request.headers.get("content-type", "")
            if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
                try:
                    form = await request.form()
                    request.state.form_data = form
                except Exception:
                    request.state.form_data = {}
            elif "application/json" in content_type:
                try:
                    cached_body = await request.body()
                    body = json.loads(cached_body.decode("utf-8")) if cached_body else {}
                    request.state.json_data = body if isinstance(body, dict) else {}
                except Exception:
                    request.state.json_data = {}

        token = _request_context.set(request)
        try:
            if cached_body is None:
                await self.app(scope, receive, send)
                return

            sent_body = False

            async def replay_cached_body():
                nonlocal sent_body
                if sent_body:
                    return {"type": "http.request", "body": b"", "more_body": False}
                sent_body = True
                return {"type": "http.request", "body": cached_body, "more_body": False}

            await self.app(scope, replay_cached_body, send)
        finally:
            _request_context.reset(token)


def get_current_request() -> Request | None:
    try:
        return _request_context.get()
    except LookupError:
        return None


def get_session() -> dict:
    req = get_current_request()
    if req is not None:
        return req.session
    return {}


class SessionProxy:
    def _get_sess(self):
        req = get_current_request()
        if req is None:
            return {}
        return req.session

    def __getitem__(self, key):
        return self._get_sess()[key]

    def __setitem__(self, key, value):
        self._get_sess()[key] = value

    def __delitem__(self, key):
        del self._get_sess()[key]

    def __contains__(self, key):
        return key in self._get_sess()

    def get(self, key, default=None):
        return self._get_sess().get(key, default)

    def pop(self, key, default=None):
        sess = self._get_sess()
        if key in sess:
            return sess.pop(key)
        return default

    def clear(self):
        self._get_sess().clear()

    def update(self, *args, **kwargs):
        self._get_sess().update(*args, **kwargs)

    def setdefault(self, key, default=None):
        return self._get_sess().setdefault(key, default)

    def keys(self):
        return self._get_sess().keys()

    def values(self):
        return self._get_sess().values()

    def items(self):
        return self._get_sess().items()

    def __str__(self):
        return str(self._get_sess())

    def __repr__(self):
        return repr(self._get_sess())

    @property
    def permanent(self):
        return True

    @permanent.setter
    def permanent(self, value):
        pass


class UploadFileWrapper:
    def __init__(self, upload_file: UploadFile):
        self._uf = upload_file
        self.filename = upload_file.filename
        self.content_type = upload_file.content_type
        self.stream = upload_file.file

    def read(self, *args, **kwargs):
        self._uf.file.seek(0)
        return self._uf.file.read(*args, **kwargs)

    def save(self, destination, buffer_size=16384):
        self._uf.file.seek(0)
        if isinstance(destination, str):
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            with open(destination, "wb") as f:
                shutil.copyfileobj(self._uf.file, f)
        else:
            shutil.copyfileobj(self._uf.file, destination)


class RequestProxy:
    def _get_req(self) -> Request:
        req = get_current_request()
        if req is None:
            raise RuntimeError("Working outside of request context.")
        return req

    @property
    def method(self) -> str:
        return self._get_req().method

    @property
    def path(self) -> str:
        return self._get_req().url.path

    @property
    def headers(self) -> dict:
        return self._get_req().headers

    @property
    def args(self):
        return self._get_req().query_params

    @property
    def form(self):
        return getattr(self._get_req().state, "form_data", {})

    def get_json(self, silent=False):
        return getattr(self._get_req().state, "json_data", {})

    @property
    def is_json(self) -> bool:
        ct = self._get_req().headers.get("content-type", "")
        return "application/json" in ct

    @property
    def remote_addr(self) -> str:
        req = self._get_req()
        if req.client:
            return req.client.host
        return "127.0.0.1"

    @property
    def referrer(self) -> str:
        return self._get_req().headers.get("referer", "")

    @property
    def host(self) -> str:
        return self._get_req().headers.get("host", "")

    @property
    def files(self):
        form_data = getattr(self._get_req().state, "form_data", {})
        files_dict = {}
        for key, value in form_data.items():
            if isinstance(value, UploadFile):
                files_dict[key] = UploadFileWrapper(value)
        return files_dict


class CurrentAppProxy:
    def __getattr__(self, name):
        req = get_current_request()
        if req is None:
            raise RuntimeError("Working outside of request context.")
        if name == "root_path":
            return getattr(req.app, "backend_root_path", "")
        return getattr(req.app, name)


session = SessionProxy()
request = RequestProxy()
current_app = CurrentAppProxy()
