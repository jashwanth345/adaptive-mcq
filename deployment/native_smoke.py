"""Verify the retained native configuration through the actual supervisor, then stop."""

import json
from urllib.request import ProxyHandler, build_opener

from backend.app.config import PROJECT_ROOT, load_settings
from deployment import local


def main():
    settings = load_settings()
    opener = build_opener(ProxyHandler({}))
    original_sleep = local.time.sleep
    checked = []

    def stop_after_ready(delay):
        if delay == 0.5:
            with opener.open(
                settings.frontend_origin + "/api/v1/health/ready", timeout=5
            ) as response:
                assert json.load(response)["status"] == "ready"
            with opener.open(
                settings.frontend_origin + "/login", timeout=5
            ) as response:
                assert response.status == 200 and b"<html" in response.read()
                assert (
                    "script-src 'self'" in response.headers["Content-Security-Policy"]
                )
            checked.append(
                "native frontend/API proxy, login route and browser security headers"
            )
            raise KeyboardInterrupt
        original_sleep(delay)

    try:
        local.time.sleep = stop_after_ready
        local.start(settings)
    finally:
        local.time.sleep = original_sleep
    assert checked
    local.assert_ports_free(settings)
    report = {
        "status": "passed",
        "checks": checked + ["both application children stopped and ports released"],
        "configuration": "retained native database; mock AI; prepared local assets",
        "model_inference": False,
    }
    (PROJECT_ROOT / "docs/evidence/phase-22-native-startup.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
