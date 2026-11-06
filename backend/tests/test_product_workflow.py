"""HTTP + real Postgres acceptance checks; provider data and identity are fixtures."""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import main
from analysis_job_worker import run_analysis_job
from auth import CurrentUser, get_current_user
from test_analysis_job_worker import _fake_deps


@pytest.fixture
def product_client(require_postgres, monkeypatch):
    identity = {"id": f"test-user-{uuid4()}"}
    main.app.dependency_overrides[get_current_user] = lambda: CurrentUser(id=identity["id"], email=None)
    monkeypatch.setattr(main, "run_analysis_job", lambda job_id, user_id, ticker: run_analysis_job(
        job_id, user_id, ticker, deps=_fake_deps(),
    ))
    try:
        with TestClient(main.app) as client:
            yield client, identity
    finally:
        main.app.dependency_overrides.clear()


def test_submit_and_read_persisted_analysis(product_client):
    client, _ = product_client
    submitted = client.post("/api/v1/analysis-jobs", json={"ticker": "aapl"})
    assert submitted.status_code == 202
    # TestClient waits for background tasks; this does not measure live polling latency.
    job = client.get(f"/api/v1/analysis-jobs/{submitted.json()['id']}")
    assert job.status_code == 200
    body = job.json()
    assert body["status"] == "complete"
    assert body["result"]["ticker"] == "AAPL"
    assert body["result"]["assessment"] == "Bullish"
    assert body["started_at"] is not None
    assert body["completed_at"] is not None


def test_analysis_is_only_readable_by_its_owner(product_client):
    client, identity = product_client
    submitted = client.post("/api/v1/analysis-jobs", json={"ticker": "AAPL"})
    identity["id"] = f"other-user-{uuid4()}"
    response = client.get(f"/api/v1/analysis-jobs/{submitted.json()['id']}")
    assert response.status_code == 404


def test_watchlist_add_duplicate_reload_and_remove(product_client):
    client, _ = product_client
    assert client.get("/api/v1/watchlist").json()["items"] == []
    assert client.post("/api/v1/watchlist/items", json={"ticker": "aapl"}).status_code == 201
    assert client.post("/api/v1/watchlist/items", json={"ticker": "AAPL"}).status_code == 409
    assert [item["ticker"] for item in client.get("/api/v1/watchlist").json()["items"]] == ["AAPL"]
    assert client.delete("/api/v1/watchlist/items/AAPL").status_code == 204
    assert client.get("/api/v1/watchlist").json()["items"] == []


def test_watchlist_isolated_between_users(product_client):
    client, identity = product_client
    owner = identity["id"]
    assert client.post("/api/v1/watchlist/items", json={"ticker": "MSFT"}).status_code == 201
    identity["id"] = f"other-user-{uuid4()}"
    assert client.get("/api/v1/watchlist").json()["items"] == []
    assert client.delete("/api/v1/watchlist/items/MSFT").status_code == 404
    identity["id"] = owner
    assert [item["ticker"] for item in client.get("/api/v1/watchlist").json()["items"]] == ["MSFT"]


@pytest.mark.parametrize("ticker", ["../AAPL", "", "AAPL!"])
def test_invalid_ticker_rejected_before_job_creation(product_client, ticker):
    client, _ = product_client
    assert client.post("/api/v1/analysis-jobs", json={"ticker": ticker}).status_code == 422
