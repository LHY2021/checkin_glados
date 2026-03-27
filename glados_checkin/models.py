from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class AppConfig:
    config_path: Path
    project_root: Path
    base_url: str
    fallback_base_urls: tuple[str, ...]
    cookie: str
    user_agent: str
    run_time: str
    checkin_url: str
    status_url: str
    console_url: str
    http_proxy: str | None = None
    https_proxy: str | None = None
    timeout_seconds: int = 20

    @property
    def history_path(self) -> Path:
        return self.project_root / "data" / "checkin_history.csv"

    @property
    def base_urls(self) -> tuple[str, ...]:
        ordered = [self.base_url, *self.fallback_base_urls]
        unique: list[str] = []
        for item in ordered:
            if item and item not in unique:
                unique.append(item)
        return tuple(unique)


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    text: str
    headers: Mapping[str, str]


@dataclass(frozen=True)
class RunRecord:
    date: str
    run_at: str
    base_url: str
    result: str
    earned_points: int | None
    total_points: int | None
    total_points_status: str
    message: str


@dataclass(frozen=True)
class ProbeResult:
    active_base_url: str | None
    cookie_valid: bool | None
    total_points: int | None
    total_points_status: str
    message: str


JsonValue = dict[str, Any] | list[Any] | str | int | float | bool | None
