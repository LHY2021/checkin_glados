from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from glados_checkin.config import load_config, validate_config


class ConfigTests(unittest.TestCase):
    def test_load_config_normalizes_urls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "config.toml"
            config_path.write_text(
                "\n".join(
                    [
                        'base_url = "https://glados.rocks/"',
                        'fallback_base_urls = ["https://glados.cloud/"]',
                        'cookie = "abc"',
                        'user_agent = "UA"',
                        'run_time = "08:30"',
                        'checkin_url = "api/user/checkin"',
                        'status_url = "/api/user/status"',
                        'console_url = "console/checkin"',
                    ]
                ),
                encoding="utf-8",
            )

            config = load_config(config_path)

            self.assertEqual(config.base_url, "https://glados.rocks")
            self.assertEqual(config.fallback_base_urls, ("https://glados.cloud",))
            self.assertEqual(config.checkin_url, "/api/user/checkin")
            self.assertEqual(config.console_url, "/console/checkin")

    def test_validate_config_rejects_bad_time(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "config.toml"
            config_path.write_text(
                "\n".join(
                    [
                        'base_url = "https://glados.rocks"',
                        'fallback_base_urls = []',
                        'cookie = "abc"',
                        'user_agent = "UA"',
                        'run_time = "25:99"',
                        'checkin_url = "/api/user/checkin"',
                        'status_url = "/api/user/status"',
                        'console_url = "/console/checkin"',
                    ]
                ),
                encoding="utf-8",
            )
            config = load_config(config_path)

            self.assertIn("run_time must use HH:MM in 24-hour format.", validate_config(config))


if __name__ == "__main__":
    unittest.main()
