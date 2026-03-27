from __future__ import annotations

import argparse
from pathlib import Path

from glados_checkin.client import GladosClient
from glados_checkin.config import ConfigError, load_config, validate_config
from glados_checkin.history import append_history, read_latest_history
from glados_checkin.models import ProbeResult, RunRecord
from glados_checkin.tasks import DEFAULT_TASK_NAME, TaskInstallError, install_daily_task


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Daily GLaDOS check-in CLI.")
    parser.add_argument("--config", type=Path, default=None, help="Path to config.toml")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run", help="Run one check-in attempt and append CSV history.")
    subparsers.add_parser("status", help="Check config, cookie status, and latest history.")

    install_parser = subparsers.add_parser(
        "install-task",
        help="Register a Windows Task Scheduler task for daily execution.",
    )
    install_parser.add_argument(
        "--task-name",
        default=DEFAULT_TASK_NAME,
        help=f"Task Scheduler name. Default: {DEFAULT_TASK_NAME}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"Config error: {exc}")
        return 1

    if args.command == "run":
        return run_command(config)
    if args.command == "status":
        return status_command(config)
    if args.command == "install-task":
        return install_task_command(config, task_name=args.task_name)

    parser.error(f"Unknown command: {args.command}")
    return 2


def run_command(config) -> int:
    issues = validate_config(config, require_auth=True)
    if issues:
        print("Config validation failed:")
        for item in issues:
            print(f"- {item}")
        return 1

    client = GladosClient(config)
    record = client.run_checkin()
    append_history(record, config.history_path)
    print_run_record(record, config.history_path)
    return 0 if record.result in {"success", "partial_success", "repeat"} else 1


def status_command(config) -> int:
    issues = validate_config(config, require_auth=True)
    latest = read_latest_history(config.history_path)

    if issues:
        print("Config validation failed:")
        for item in issues:
            print(f"- {item}")
        print_latest_record(latest)
        return 1

    probe = GladosClient(config).probe_account()
    print_probe_result(probe)
    print_latest_record(latest)
    return 0 if probe.cookie_valid is not False else 1


def install_task_command(config, task_name: str) -> int:
    issues = validate_config(config, require_auth=False)
    if issues:
        print("Config validation failed:")
        for item in issues:
            print(f"- {item}")
        return 1

    try:
        message = install_daily_task(config, task_name=task_name)
    except TaskInstallError as exc:
        print(f"Task installation failed: {exc}")
        return 1

    print(f"Scheduled task ready: {task_name}")
    print(message)
    return 0


def print_run_record(record: RunRecord, history_path: Path) -> None:
    print(f"Result: {record.result}")
    print(f"Base URL: {record.base_url}")
    print(f"Earned points: {render_optional(record.earned_points)}")
    print(f"Message: {record.message}")
    print(f"History: {history_path}")


def print_probe_result(result: ProbeResult) -> None:
    print("Configuration looks valid.")
    print(f"Cookie valid: {render_cookie_valid(result.cookie_valid)}")
    print(f"Active base URL: {result.active_base_url or '-'}")
    print(f"Message: {result.message}")


def print_latest_record(record: RunRecord | None) -> None:
    print("Latest history:")
    if record is None:
        print("- No history found.")
        return
    print(f"- Date: {record.date}")
    print(f"- Run at: {record.run_at}")
    print(f"- Result: {record.result}")
    print(f"- Earned points: {render_optional(record.earned_points)}")
    print(f"- Message: {record.message}")


def render_optional(value: int | None) -> str:
    return "-" if value is None else str(value)


def render_cookie_valid(value: bool | None) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"
