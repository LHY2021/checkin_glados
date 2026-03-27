from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from glados_checkin.models import AppConfig

DEFAULT_TASK_NAME = "GLaDOS Daily Checkin"


class TaskInstallError(Exception):
    pass


def build_task_action(config: AppConfig, python_executable: str | Path | None = None) -> str:
    launcher_path = (config.project_root / "run_glados_checkin.bat").resolve()
    return f'"{launcher_path}"'


def build_schtasks_command(
    config: AppConfig,
    task_name: str = DEFAULT_TASK_NAME,
    python_executable: str | Path | None = None,
) -> list[str]:
    action = build_task_action(config, python_executable=python_executable)
    return [
        "schtasks",
        "/Create",
        "/SC",
        "DAILY",
        "/TN",
        task_name,
        "/TR",
        action,
        "/ST",
        config.run_time,
        "/F",
    ]


def install_daily_task(
    config: AppConfig,
    task_name: str = DEFAULT_TASK_NAME,
    python_executable: str | Path | None = None,
) -> str:
    if os.name != "nt":
        raise TaskInstallError("Windows Task Scheduler is only available on Windows.")

    completed = subprocess.run(
        build_schtasks_command(config, task_name=task_name, python_executable=python_executable),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        output = completed.stderr.strip() or completed.stdout.strip()
        raise TaskInstallError(output or "Failed to create scheduled task.")
    return completed.stdout.strip() or "Scheduled task created."
