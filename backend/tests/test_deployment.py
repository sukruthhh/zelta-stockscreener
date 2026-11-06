from types import SimpleNamespace

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

import auth
import main
from config import Settings


@pytest.fixture
def client():
    # These route guards do not require startup migrations or provider access.
    instance = TestClient(main.app)
    yield instance
    instance.close()


@pytest.mark.parametrize(("database", "supabase_url", "expected"), [
    (True, "https://project.supabase.co", 200),
    (False, "https://project.supabase.co", 503),
    (True, None, 503),
])
def test_readiness_requires_database_and_auth_configuration(client, monkeypatch, database, supabase_url, expected):
    monkeypatch.setattr(main, "_database_available", lambda: database)
    monkeypatch.setattr(main, "settings", SimpleNamespace(supabase_url=supabase_url))
    response = client.get("/ready")
    assert response.status_code == expected
    assert response.json()["checks"]["authentication"] == ("configured" if supabase_url else "not_configured")


@pytest.mark.parametrize(("method", "path", "body"), [
    ("GET", "/api/v1/test-ticker/AAPL", None),
    ("GET", "/api/v1/scan/history/AAPL", None),
    ("POST", "/api/v1/harvest/AAPL", None),
    ("POST", "/api/v1/scan/morning-screener", {"tickers": ["AAPL"]}),
    ("GET", "/api/v1/verification/database", None),
    ("GET", "/api/v1/anomalies", None),
    ("GET", "/api/v1/risk/AAPL", None),
    ("GET", "/api/v1/predictions", None),
    ("POST", "/api/v1/analyse/AAPL", None),
])
def test_diagnostics_are_disabled_before_any_provider_work(client, method, path, body):
    response = client.request(method, path, json=body)
    assert response.status_code == 404


def test_enabled_diagnostics_still_require_authentication():
    settings = Settings(_env_file=None, POSTGRES_URL="postgresql://unused", SUPABASE_URL="https://project.supabase.co", ENABLE_DIAGNOSTIC_ROUTES=True)
    with pytest.raises(HTTPException) as error:
        auth.require_diagnostic_access(None, settings)
    assert error.value.status_code == 401
