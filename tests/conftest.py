import pytest
from fastapi.testclient import TestClient

from app.main import app
from main import app


@pytest.fixture
def client():
    return TestClient(app)
