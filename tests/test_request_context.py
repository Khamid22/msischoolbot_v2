from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.testclient import TestClient

from backend.utils.context import RequestContextMiddleware, request as legacy_request


def test_json_body_is_available_to_legacy_proxy_and_downstream_request():
    app = FastAPI()
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
