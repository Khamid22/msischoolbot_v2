from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.testclient import TestClient

from backend.core.web.request_context import (
    RequestContextMiddleware,
    prime_body_state,
    request as legacy_request,
)


def test_json_body_is_available_to_legacy_proxy_and_downstream_request():
    # The middleware never touches the body; prime_body_state (app-level
    # dependency) parses it once, and both consumers must still see it.
    app = FastAPI(dependencies=[Depends(prime_body_state)])
    app.add_middleware(RequestContextMiddleware)

    @app.post("/echo")
    async def echo(request_obj: Request):
        return JSONResponse(
            {
                "legacy": legacy_request.get_json(silent=True),
                "downstream": await request_obj.json(),
            }
        )

    client = TestClient(app)
    response = client.post("/echo", json={"message": "hello"})

    assert response.status_code == 200
    assert response.json() == {
        "legacy": {"message": "hello"},
        "downstream": {"message": "hello"},
    }
