"""Read-only deployment checks. Does not sign in, submit jobs, or call market providers."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlsplit

import requests


def public_origin(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ValueError("Use a website origin without credentials, paths, or query parameters.")
    if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise ValueError("Public deployments must use HTTPS.")
    return value.rstrip("/")


def check_deployment(api_url: str, frontend_url: str, *, session=None) -> dict:
    api = public_origin(api_url)
    frontend = public_origin(frontend_url)
    session = session or requests.Session()
    checks = []

    def check(name, method, url, expected_status, *, headers=None, validate=None):
        try:
            response = session.request(method, url, headers=headers, timeout=20, allow_redirects=False)
            passed = response.status_code == expected_status
            if passed and validate:
                passed = bool(validate(response))
            checks.append({"name": name, "passed": passed, "status": response.status_code})
        except Exception:
            # Never persist response bodies or arbitrary exception text containing credentials.
            checks.append({"name": name, "passed": False, "error": "Request failed or response was invalid."})

    check("api_ready", "GET", f"{api}/ready", 200, validate=lambda response: response.json().get("status") == "ready")
    check("unauthenticated_watchlist_blocked", "GET", f"{api}/api/v1/watchlist", 401)
    check("diagnostics_disabled", "GET", f"{api}/api/v1/verification/database", 404)
    check("raw_predictions_disabled", "GET", f"{api}/api/v1/predictions", 404)
    check("frontend_origin_allowed", "OPTIONS", f"{api}/api/v1/watchlist", 200, headers={
        "Origin": frontend, "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization",
    }, validate=lambda response: response.headers.get("access-control-allow-origin") == frontend)
    check("frontend_loads", "GET", frontend, 200, validate=lambda response: "Zelta" in response.text)
    check("manifest_loads", "GET", f"{frontend}/manifest.json", 200, validate=lambda response: response.json().get("short_name") == "Zelta")
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "api_url": api, "frontend_url": frontend,
        "passed": all(check["passed"] for check in checks), "checks": checks,
        "limitations": "Read-only connectivity/configuration checks. Real email delivery, JWT verification, analysis, watchlists and phone installation still need authenticated verification.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--frontend-url", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = check_deployment(args.api_url, args.frontend_url)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
