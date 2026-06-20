import re
import inspect
from functools import wraps
from fastapi import APIRouter
from fastapi.responses import JSONResponse, HTMLResponse
from starlette.responses import Response as StarletteResponse


_LEGACY_PATH_RE = re.compile(r"<([a-zA-Z_][a-zA-Z0-9_]*:)?([a-zA-Z_][a-zA-Z0-9_]*)>")


def convert_legacy_path(path: str) -> str:
    return _LEGACY_PATH_RE.sub(r"{\2}", path)


class LegacyRouteAdapter(APIRouter):
    def __init__(self, *args, **kwargs):
        prefix = kwargs.pop("url_prefix", None)
        if prefix:
            kwargs["prefix"] = prefix
        kwargs.pop("static_folder", None)
        kwargs.pop("static_url_path", None)
        kwargs.pop("template_folder", None)
        super().__init__(**kwargs)
        self._before_request_funcs = []

    def before_request(self, func):
        self._before_request_funcs.append(func)
        return func

    def add_api_route(self, path: str, endpoint, **kwargs):
        # Support legacy <int:id> route parameters while routes are migrated.
        matches = _LEGACY_PATH_RE.findall(path)
        # Convert path to FastAPI curly-bracket syntax
        converted_path = _LEGACY_PATH_RE.sub(r"{\2}", path)

        # Detect integer parameters to cast them dynamically
        int_params = set()
        for type_prefix, name in matches:
            if type_prefix == "int:":
                int_params.add(name)

        def handle_result(res):
            if isinstance(res, tuple) and len(res) == 2:
                body, status_code = res
                if isinstance(status_code, int):
                    if isinstance(body, StarletteResponse):
                        body.status_code = status_code
                        return body
                    elif isinstance(body, str):
                        return HTMLResponse(content=body, status_code=status_code)
                    else:
                        # body could be dict, list, string, etc.
                        return JSONResponse(content=body, status_code=status_code)
            if isinstance(res, str):
                return HTMLResponse(content=res)
            return res

        orig_endpoint = endpoint

        if inspect.iscoroutinefunction(orig_endpoint):
            @wraps(orig_endpoint)
            async def wrapped(*args, **wrapped_kwargs):
                for hook in self._before_request_funcs:
                    hook_res = hook()
                    if hook_res is not None:
                        return handle_result(hook_res)

                for name in int_params:
                    if name in wrapped_kwargs:
                        try:
                            wrapped_kwargs[name] = int(wrapped_kwargs[name])
                        except (TypeError, ValueError):
                            pass
                res = await orig_endpoint(*args, **wrapped_kwargs)
                return handle_result(res)
        else:
            @wraps(orig_endpoint)
            def wrapped(*args, **wrapped_kwargs):
                for hook in self._before_request_funcs:
                    hook_res = hook()
                    if hook_res is not None:
                        return handle_result(hook_res)

                for name in int_params:
                    if name in wrapped_kwargs:
                        try:
                            wrapped_kwargs[name] = int(wrapped_kwargs[name])
                        except (TypeError, ValueError):
                            pass
                res = orig_endpoint(*args, **wrapped_kwargs)
                return handle_result(res)

        endpoint = wrapped

        super().add_api_route(converted_path, endpoint, **kwargs)


RouteGroup = LegacyRouteAdapter
