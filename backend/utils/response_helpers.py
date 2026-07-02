from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi import HTTPException


def jsonify(*args, status_code: int = 200, **kwargs):
    if args:
        if len(args) == 1:
            # If the user did jsonify({"key": "val"}), content is args[0]
            content = args[0]
        else:
            content = list(args)
    else:
        content = kwargs

    return JSONResponse(content=content, status_code=status_code)


def with_status(response: Response, status_code: int) -> Response:
    """Return the response with its status code replaced."""
    response.status_code = status_code
    return response


def redirect(location: str, code: int = 302):
    return RedirectResponse(url=location, status_code=code)


def abort(code: int, description: str = None):
    raise HTTPException(status_code=code, detail=description or "")
