from types import SimpleNamespace

import pytest

from scripts.check_deployment import check_deployment, public_origin


class DeploymentSession:
    def __init__(self, *, auth_status=401, cors_origin="https://site.example.com"):
        self.auth_status = auth_status
        self.cors_origin = cors_origin

    def request(self, method, url, **kwargs):
        status = 200
        body = {}
        headers = {}
        if method == "OPTIONS":
            headers["access-control-allow-origin"] = self.cors_origin
        elif url.endswith("/ready"):
            body = {"status": "ready"}
        elif url.endswith("/watchlist"):
            status = self.auth_status
        elif url.endswith("/verification/database") or url.endswith("/predictions"):
            status = 404
        elif url.endswith("/manifest.json"):
            body = {"short_name": "Zelta"}
        return SimpleNamespace(status_code=status, headers=headers, json=lambda: body, text="Zelta")


def test_deployment_check_detects_accidentally_public_watchlists():
    result = check_deployment("https://api.example.com", "https://site.example.com", session=DeploymentSession(auth_status=200))
    assert not result["passed"]
    assert next(item for item in result["checks"] if item["name"] == "unauthenticated_watchlist_blocked")["passed"] is False


def test_deployment_check_detects_wrong_cors_origin():
    result = check_deployment("https://api.example.com", "https://site.example.com", session=DeploymentSession(cors_origin="https://wrong.example.com"))
    assert not result["passed"]


def test_deployment_check_passes_only_the_defined_connectivity_checks():
    result = check_deployment("https://api.example.com", "https://site.example.com", session=DeploymentSession())
    assert result["passed"]
    assert len(result["checks"]) == 7


@pytest.mark.parametrize("url", ["http://public.example.com", "https://user:password@example.com", "https://example.com?token=secret"])
def test_deployment_check_rejects_insecure_or_credential_bearing_origins(url):
    with pytest.raises(ValueError):
        public_origin(url)
