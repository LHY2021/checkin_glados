from __future__ import annotations

import csv
from pathlib import Path

from glados_checkin.models import RunRecord

CSV_HEADERS = [
    "date",
    "run_at",
    "base_url",
    "result",
    "earned_points",
    "total_points",
    "total_points_status",
    "message",
]


def append_history(record: RunRecord, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_HEADERS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(
            {
                "date": record.date,
                "run_at": record.run_at,
                "base_url": record.base_url,
                "result": record.result,
                "earned_points": "" if record.earned_points is None else record.earned_points,
                "total_points": "" if record.total_points is None else record.total_points,
                "total_points_status": record.total_points_status,
                "message": record.message,
            }
        )


def read_latest_history(path: Path) -> RunRecord | None:
    if not path.exists():
        return None

    latest_row: dict[str, str] | None = None
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            latest_row = row

    if latest_row is None:
        return None

    return RunRecord(
        date=latest_row["date"],
        run_at=latest_row["run_at"],
        base_url=latest_row["base_url"],
        result=latest_row["result"],
        earned_points=parse_optional_int(latest_row["earned_points"]),
        total_points=parse_optional_int(latest_row["total_points"]),
        total_points_status=latest_row["total_points_status"],
        message=latest_row["message"],
    )


def parse_optional_int(value: str) -> int | None:
    text = value.strip()
    if not text:
        return None
    return int(text)
