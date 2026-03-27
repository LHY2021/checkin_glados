from __future__ import annotations

from pathlib import Path

from glados_checkin.models import AppConfig, HttpResponse


def build_config(root: Path) -> AppConfig:
    return AppConfig(
        config_path=root / "config.toml",
        project_root=root,
        base_url="https://glados.rocks",
        fallback_base_urls=("https://glados.cloud",),
        cookie="koa:sess=abc123",
        user_agent="UnitTestAgent/1.0",
        run_time="09:00",
        checkin_url="/api/user/checkin",
        status_url="/api/user/status",
        console_url="/console/checkin",
    )


def json_response(status_code: int, payload: object) -> HttpResponse:
    import json

    return HttpResponse(
        status_code=status_code,
        text=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )


def text_response(status_code: int, text: str) -> HttpResponse:
    return HttpResponse(
        status_code=status_code,
        text=text,
        headers={"Content-Type": "text/html"},
    )
