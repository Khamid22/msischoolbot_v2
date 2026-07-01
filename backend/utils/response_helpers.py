from fastapi.responses import JSONResponse, RedirectResponse
from fastapi import HTTPException


def jsonify(*args, **kwargs):
    if args:
        if len(args) == 1:
            # If the user did jsonify({"key": "val"}), content is args[0]
            content = args[0]
        else:
            content = list(args)
    else:
        content = kwargs

    # Starlette JSONResponse expects serializable dict/list/etc. Endpoints that
    # need a status code can return (jsonify(...), status_code).
    return JSONResponse(content=content)


def redirect(location: str, code: int = 302):
    return RedirectResponse(url=location, status_code=code)


def abort(code: int, description: str = None):
    raise HTTPException(status_code=code, detail=description or "")


class DummyCsrf:
    def exempt(self, f):
        return f


csrf = DummyCsrf()
