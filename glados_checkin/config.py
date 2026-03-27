from __future__ import annotations

import os
import re
import tomllib
from pathlib import Path

from glados_checkin.models import AppConfig

DEFAULT_BASE_URL = "https://glados.one"
DEFAULT_FALLBACK_BASE_URLS = ("https://glados.rocks", "https://glados.cloud")
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)
DEFAULT_RUN_TIME = "09:00"
DEFAULT_CHECKIN_URL = "/api/user/checkin"
DEFAULT_STATUS_URL = "/api/user/status"
DEFAULT_CONSOLE_URL = "/console/checkin"


class ConfigError(Exception):
    pass


def default_config_path() -> Path:
    env_path = os.environ.get("GLADOS_CHECKIN_CONFIG")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return Path.cwd() / "config.toml"


def load_config(path: str | Path | None = None) -> AppConfig:
    config_path = Path(path).expanduser().resolve() if path else default_config_path()
    if not config_path.exists():
        raise ConfigError(
            f"Config file not found: {config_path}. Copy config.example.toml to config.toml first."
        )

    try:
        raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in {config_path}: {exc}") from exc

    project_root = config_path.parent
    base_url = normalize_base_url(raw.get("base_url", DEFAULT_BASE_URL))
    fallback_base_urls = tuple(
        normalize_base_url(item)
        for item in raw.get("fallback_base_urls", list(DEFAULT_FALLBACK_BASE_URLS))
        if str(item).strip()
    )

    return AppConfig(
        config_path=config_path,
        project_root=project_root,
        base_url=base_url,
        fallback_base_urls=fallback_base_urls,
        cookie=str(raw.get("cookie", "")).strip(),
        user_agent=str(raw.get("user_agent", DEFAULT_USER_AGENT)).strip(),
        run_time=str(raw.get("run_time", DEFAULT_RUN_TIME)).strip(),
        checkin_url=normalize_url_path(raw.get("checkin_url", DEFAULT_CHECKIN_URL)),
        status_url=normalize_url_path(raw.get("status_url", DEFAULT_STATUS_URL)),
        console_url=normalize_url_path(raw.get("console_url", DEFAULT_CONSOLE_URL)),
        http_proxy=normalize_optional_url(raw.get("http_proxy")),
        https_proxy=normalize_optional_url(raw.get("https_proxy")),
    )


def validate_config(config: AppConfig, require_auth: bool = True) -> list[str]:
    issues: list[str] = []
    if not is_valid_base_url(config.base_url):
        issues.append("base_url must be an absolute https URL.")
    for item in config.fallback_base_urls:
        if not is_valid_base_url(item):
            issues.append(f"fallback base URL is invalid: {item}")
    if require_auth and not config.cookie:
        issues.append("cookie is required.")
    if require_auth and not config.user_agent:
        issues.append("user_agent is required.")
    if not is_valid_time(config.run_time):
        issues.append("run_time must use HH:MM in 24-hour format.")
    for path_name in ("checkin_url", "status_url", "console_url"):
        value = getattr(config, path_name)
        if not value.startswith("/"):
            issues.append(f"{path_name} must start with '/'.")
    for proxy_name in ("http_proxy", "https_proxy"):
        value = getattr(config, proxy_name)
        if value and not is_valid_proxy_url(value):
            issues.append(f"{proxy_name} must start with http:// or https://.")
    return issues


def normalize_base_url(value: object) -> str:
    text = str(value).strip()
    return text.rstrip("/")


def normalize_url_path(value: object) -> str:
    text = str(value).strip()
    if not text.startswith("/"):
        text = f"/{text}"
    return text


def normalize_optional_url(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def is_valid_time(value: str) -> bool:
    match = re.fullmatch(r"(\d{2}):(\d{2})", value)
    if not match:
        return False
    hours = int(match.group(1))
    minutes = int(match.group(2))
    return 0 <= hours <= 23 and 0 <= minutes <= 59


def is_valid_base_url(value: str) -> bool:
    return value.startswith("https://") and len(value) > len("https://")


def is_valid_proxy_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")
