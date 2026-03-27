from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Protocol

from glados_checkin.models import AppConfig, HttpResponse, ProbeResult, RunRecord

KNOWN_CHECKIN_TOKENS = ("glados.network", "glados_network", "glados.one")
AUTH_HINTS = (
    "login",
    "log in",
    "sign in",
    "unauthorized",
    "forbidden",
    "cookie",
    "expired",
    "auth",
)
REPEAT_HINTS = ("repeat", "already", "tomorrow")
SUCCESS_HINTS = ("checkin", "success", "got", "points")
FAILURE_HINTS = ("fail", "error", "invalid", "denied")
TOTAL_POINT_KEYS = (
    "total_points",
    "totalPoints",
    "current_points",
    "currentPoints",
    "points_balance",
    "pointsBalance",
    "balance",
    "credits",
    "score",
    "currentScore",
    "user_points",
    "userPoints",
)
STATUS_POINT_KEYS = TOTAL_POINT_KEYS + ("points", "point")
EARNED_POINT_KEYS = (
    "earned_points",
    "earnedPoints",
    "points_earned",
    "pointsEarned",
    "reward_points",
    "rewardPoints",
    "points",
)


class TransportError(Exception):
    pass


class AuthError(Exception):
    pass


class HttpTransport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None = None,
        timeout: int = 20,
    ) -> HttpResponse:
        ...


class UrllibTransport:
    def __init__(self, proxies: dict[str, str] | None = None) -> None:
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler(proxies or {}))

    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None = None,
        timeout: int = 20,
    ) -> HttpResponse:
        request = urllib.request.Request(url=url, data=body, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=timeout) as response:
                text = response.read().decode("utf-8", errors="replace")
                return HttpResponse(
                    status_code=response.status,
                    text=text,
                    headers=dict(response.headers.items()),
                )
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            return HttpResponse(
                status_code=exc.code,
                text=text,
                headers=dict(exc.headers.items()),
            )
        except urllib.error.URLError as exc:
            raise TransportError(str(exc.reason)) from exc


class GladosClient:
    def __init__(self, config: AppConfig, transport: HttpTransport | None = None) -> None:
        self.config = config
        self.transport = transport or UrllibTransport(self._proxy_map())

    def run_checkin(self) -> RunRecord:
        now = datetime.now().astimezone()
        auth_messages: list[str] = []
        network_messages: list[str] = []

        for base_url in self.config.base_urls:
            try:
                return self._run_checkin_for_base(base_url, now)
            except AuthError as exc:
                auth_messages.append(f"{base_url}: {exc}")
            except TransportError as exc:
                network_messages.append(f"{base_url}: {exc}")

        result = "auth_error" if auth_messages else "network_error"
        message = "; ".join(auth_messages or network_messages) or "All configured base URLs failed."
        return RunRecord(
            date=now.date().isoformat(),
            run_at=now.isoformat(timespec="seconds"),
            base_url=self.config.base_url,
            result=result,
            earned_points=None,
            total_points=None,
            total_points_status="missing",
            message=message,
        )

    def probe_account(self) -> ProbeResult:
        auth_messages: list[str] = []
        network_messages: list[str] = []

        for base_url in self.config.base_urls:
            try:
                response = self._request(
                    "GET",
                    self._url(base_url, self.config.status_url),
                    headers=self._browser_headers(base_url),
                )
            except TransportError as exc:
                network_messages.append(f"{base_url}: {exc}")
                continue

            payload = safe_json_loads(response.text)
            if self._is_auth_failure(response, payload):
                auth_messages.append(f"{base_url}: authentication failed")
                continue

            return ProbeResult(
                active_base_url=base_url,
                cookie_valid=True,
                total_points=None,
                total_points_status="not_requested",
                message="Cookie is valid.",
            )

        if auth_messages:
            return ProbeResult(
                active_base_url=None,
                cookie_valid=False,
                total_points=None,
                total_points_status="missing",
                message="; ".join(auth_messages),
            )

        return ProbeResult(
            active_base_url=None,
            cookie_valid=None,
            total_points=None,
            total_points_status="missing",
            message="; ".join(network_messages) or "No configured base URL could be reached.",
        )

    def _run_checkin_for_base(self, base_url: str, now: datetime) -> RunRecord:
        response, payload = self._post_checkin(base_url)
        if self._is_auth_failure(response, payload):
            raise AuthError(extract_message(payload) or f"HTTP {response.status_code}")

        classification = classify_checkin(response, payload)
        if classification == "auth_error":
            raise AuthError(extract_message(payload) or f"HTTP {response.status_code}")
        if classification == "network_error":
            raise TransportError(extract_message(payload) or f"HTTP {response.status_code}")

        message = extract_message(payload) or f"HTTP {response.status_code}"
        earned_points = extract_earned_points(payload, message)
        result = "repeat" if classification == "repeat" else "success"

        return RunRecord(
            date=now.date().isoformat(),
            run_at=now.isoformat(timespec="seconds"),
            base_url=base_url,
            result=result,
            earned_points=earned_points,
            total_points=None,
            total_points_status="not_requested",
            message=message,
        )

    def _post_checkin(self, base_url: str) -> tuple[HttpResponse, Any]:
        url = self._url(base_url, self.config.checkin_url)
        headers = self._browser_headers(base_url)
        headers["Content-Type"] = "application/json;charset=UTF-8"

        last_response: HttpResponse | None = None
        last_payload: Any = None

        for token in KNOWN_CHECKIN_TOKENS:
            body = json.dumps({"token": token}).encode("utf-8")
            response = self._request("POST", url, headers=headers, body=body)
            payload = safe_json_loads(response.text)

            if response.status_code >= 500 or response.status_code == 404:
                raise TransportError(f"HTTP {response.status_code}")

            last_response = response
            last_payload = payload
            if not should_retry_with_other_token(response, payload):
                break

        if last_response is None:
            raise TransportError("No check-in response received.")
        return last_response, last_payload

    def _get_status_points(self, base_url: str) -> int | None:
        try:
            response = self._request(
                "GET",
                self._url(base_url, self.config.status_url),
                headers=self._browser_headers(base_url),
            )
        except TransportError:
            return None

        payload = safe_json_loads(response.text)
        if self._is_auth_failure(response, payload):
            return None
        return extract_total_points(payload, context="status")

    def _get_console_points(self, base_url: str) -> int | None:
        try:
            response = self._request(
                "GET",
                self._url(base_url, self.config.console_url),
                headers=self._browser_headers(base_url),
            )
        except TransportError:
            return None

        if self._is_auth_failure(response, None):
            return None
        return extract_total_points_from_html(response.text)

    def _request(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None = None,
    ) -> HttpResponse:
        return self.transport.request(
            method=method,
            url=url,
            headers=headers,
            body=body,
            timeout=self.config.timeout_seconds,
        )

    def _browser_headers(self, base_url: str) -> dict[str, str]:
        return {
            "Accept": "application/json, text/plain, */*",
            "Cookie": self.config.cookie,
            "Origin": base_url,
            "Referer": self._url(base_url, self.config.console_url),
            "User-Agent": self.config.user_agent,
        }

    def _proxy_map(self) -> dict[str, str]:
        proxies: dict[str, str] = {}
        if self.config.http_proxy:
            proxies["http"] = self.config.http_proxy
        if self.config.https_proxy:
            proxies["https"] = self.config.https_proxy
        return proxies

    def _is_auth_failure(self, response: HttpResponse, payload: Any) -> bool:
        if response.status_code in (401, 403):
            return True
        message = (extract_message(payload) or response.text[:200]).lower()
        return any(hint in message for hint in AUTH_HINTS)

    @staticmethod
    def _url(base_url: str, path: str) -> str:
        return f"{base_url}{path}"


def safe_json_loads(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def should_retry_with_other_token(response: HttpResponse, payload: Any) -> bool:
    if response.status_code not in (400, 422):
        return False
    message = (extract_message(payload) or response.text[:200]).lower()
    return "token" in message or "payload" in message


def classify_checkin(response: HttpResponse, payload: Any) -> str:
    if response.status_code >= 500:
        return "network_error"
    if response.status_code in (401, 403):
        return "auth_error"

    message = (extract_message(payload) or "").lower()
    code = extract_numeric_from_key(payload, "code")

    if code == 1 or any(hint in message for hint in REPEAT_HINTS):
        return "repeat"
    if code == 0:
        return "success"
    if any(hint in message for hint in AUTH_HINTS):
        return "auth_error"
    if any(hint in message for hint in FAILURE_HINTS) and not any(
        hint in message for hint in SUCCESS_HINTS
    ):
        return "network_error"
    if response.status_code >= 400:
        return "network_error"
    return "success"


def extract_message(payload: Any) -> str | None:
    if isinstance(payload, dict):
        for key in ("message", "msg", "detail", "reason", "description", "error"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def extract_earned_points(payload: Any, message: str) -> int | None:
    points = find_first_numeric(payload, EARNED_POINT_KEYS)
    if points is not None:
        return points

    match = re.search(r"(\d+)\s*points?", message, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def extract_total_points(payload: Any, context: str) -> int | None:
    if payload is None:
        return None

    keys = STATUS_POINT_KEYS if context == "status" else TOTAL_POINT_KEYS
    points = find_first_numeric(payload, keys)
    if points is not None:
        return points

    if isinstance(payload, dict):
        for key in ("data", "result", "profile", "user"):
            nested = payload.get(key)
            nested_points = find_first_numeric(nested, keys)
            if nested_points is not None:
                return nested_points
    return None


def extract_total_points_from_html(text: str) -> int | None:
    patterns = (
        r'"totalPoints"\s*:\s*(\d+)',
        r'"total_points"\s*:\s*(\d+)',
        r'"currentPoints"\s*:\s*(\d+)',
        r'"pointsBalance"\s*:\s*(\d+)',
        r'"credits"\s*:\s*(\d+)',
        r'"score"\s*:\s*(\d+)',
        r"total points[^0-9]{0,10}(\d+)",
        r"current points[^0-9]{0,10}(\d+)",
        r"积分[^0-9]{0,10}(\d+)",
    )
    lowered = text.lower()
    for pattern in patterns:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def find_first_numeric(payload: Any, keys: tuple[str, ...]) -> int | None:
    normalized_keys = {normalize_key(key) for key in keys}
    return _find_first_numeric(payload, normalized_keys)


def _find_first_numeric(payload: Any, normalized_keys: set[str]) -> int | None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if normalize_key(key) in normalized_keys:
                parsed = parse_int(value)
                if parsed is not None:
                    return parsed
        for value in payload.values():
            parsed = _find_first_numeric(value, normalized_keys)
            if parsed is not None:
                return parsed
    elif isinstance(payload, list):
        for item in payload:
            parsed = _find_first_numeric(item, normalized_keys)
            if parsed is not None:
                return parsed
    return None


def extract_numeric_from_key(payload: Any, key: str) -> int | None:
    return find_first_numeric(payload, (key,))


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def parse_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        match = re.fullmatch(r"\d+", value.strip())
        if match:
            return int(match.group(0))
    return None
