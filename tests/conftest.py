import os
import sys

# Import-time config needs these before backend.server loads. Placeholders only:
# no test opens a real database connection or talks to Telegram.
os.environ.setdefault("APP_ENV", "dev")
os.environ.setdefault("BOT_TOKEN", "123456:test-placeholder")
os.environ.setdefault("MINI_APP_URL", "https://example.com")
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from starlette.testclient import TestClient


@pytest.fixture(scope="session")
def app():
    from backend.server import create_app

    test_app = create_app()
    test_app.state.testing = True
    return test_app


@pytest.fixture()
def client(app):
    return TestClient(app, follow_redirects=False)
