from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from glados_checkin.tasks import build_schtasks_command, build_task_action
from tests.test_helpers import build_config


class TaskTests(unittest.TestCase):
    def test_build_task_action_points_to_local_launcher(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = build_config(root)

            action = build_task_action(config, python_executable=root / "python.exe")

            self.assertIn("run_glados_checkin.bat", action)
            self.assertTrue(action.startswith('"'))

    def test_build_schtasks_command_contains_schedule(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = build_config(root)

            command = build_schtasks_command(config, task_name="Daily Test")

            self.assertEqual(command[0], "schtasks")
            self.assertIn("09:00", command)
            self.assertIn("Daily Test", command)


if __name__ == "__main__":
    unittest.main()
