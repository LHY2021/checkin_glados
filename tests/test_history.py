from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from glados_checkin.history import append_history, read_latest_history
from glados_checkin.models import RunRecord


class HistoryTests(unittest.TestCase):
    def test_append_and_read_latest_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = Path(temp_dir) / "data" / "checkin_history.csv"
            append_history(
                RunRecord(
                    date="2026-03-26",
                    run_at="2026-03-26T09:00:00+08:00",
                    base_url="https://glados.rocks",
                    result="success",
                    earned_points=5,
                    total_points=50,
                    total_points_status="from_status",
                    message="Checkin! Got 5 points",
                ),
                history_path,
            )

            latest = read_latest_history(history_path)

            self.assertIsNotNone(latest)
            self.assertEqual(latest.result, "success")
            self.assertEqual(latest.total_points, 50)


if __name__ == "__main__":
    unittest.main()
