"""Role-guard support for native FastAPI dependencies.

FastAPI dependencies cannot short-circuit a request by *returning* a response
the way Flask's before_request hooks could. Guards instead raise
``GuardResponse`` carrying the exact response to send; the handler installed
by ``install_guard_handler`` unwraps it.
"""

from fastapi import Request


class GuardResponse(Exception):
    """Raised by a guard dependency to short-circuit with a prebuilt response."""

    def __init__(self, response):
        super().__init__("guard response")
        self.response = response


def install_guard_handler(app):
    @app.exception_handler(GuardResponse)
    def _handle_guard_response(request: Request, exc: GuardResponse):
        return exc.response
