from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from glados_checkin.client import GladosClient, TransportError
from glados_checkin.models import HttpResponse
from tests.test_helpers import build_config, json_response, text_response


class FakeTransport:
    def __init__(self, responses: dict[tuple[str, str], list[HttpResponse | Exception]]) -> None:
        self.responses = {key: list(value) for key, value in responses.items()}

    def request(self, method, url, headers, body=None, timeout=20):
        key = (method, url)
        if key not in self.responses or not self.responses[key]:
            raise AssertionError(f"Unexpected request: {method} {url}")
        response = self.responses[key].pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class ClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.config = build_config(self.root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_run_success_without_total_points_lookup(self) -> None:
        transport = FakeTransport(
            {
                ("POST", "https://glados.rocks/api/user/checkin"): [
                    json_response(200, {"message": "Checkin! Got 5 points", "points": 5})
                ],
            }
        )
        record = GladosClient(self.config, transport=transport).run_checkin()

        self.assertEqual(record.result, "success")
        self.assertEqual(record.earned_points, 5)
        self.assertIsNone(record.total_points)
        self.assertEqual(record.total_points_status, "not_requested")

    def test_run_success_when_total_points_are_unavailable(self) -> None:
        transport = FakeTransport(
            {
                ("POST", "https://glados.rocks/api/user/checkin"): [
                    json_response(200, {"message": "Checkin! Got 2 points", "points": 2})
                ],
            }
        )
        record = GladosClient(self.config, transport=transport).run_checkin()

        self.assertEqual(record.result, "success")
        self.assertEqual(record.earned_points, 2)
        self.assertIsNone(record.total_points)
        self.assertEqual(record.total_points_status, "not_requested")

    def test_run_falls_back_to_second_domain(self) -> None:
        transport = FakeTransport(
            {
                ("POST", "https://glados.rocks/api/user/checkin"): [
                    TransportError("timed out")
                ],
                ("POST", "https://glados.cloud/api/user/checkin"): [
                    json_response(200, {"message": "Checkin Repeats!", "points": 0})
                ],
            }
        )
        record = GladosClient(self.config, transport=transport).run_checkin()

        self.assertEqual(record.result, "repeat")
        self.assertEqual(record.base_url, "https://glados.cloud")
        self.assertIsNone(record.total_points)

    def test_auth_error_when_cookie_invalid_everywhere(self) -> None:
        transport = FakeTransport(
            {
                ("POST", "https://glados.rocks/api/user/checkin"): [
                    json_response(401, {"message": "Please login"})
                ],
                ("POST", "https://glados.cloud/api/user/checkin"): [
                    json_response(401, {"message": "Please login"})
                ],
            }
        )
        record = GladosClient(self.config, transport=transport).run_checkin()

        self.assertEqual(record.result, "auth_error")
        self.assertIsNone(record.earned_points)
        self.assertIsNone(record.total_points)

    def test_probe_account_only_checks_cookie_validity(self) -> None:
        transport = FakeTransport(
            {
                ("GET", "https://glados.rocks/api/user/status"): [
                    json_response(200, {"data": {"leftDays": "20.5"}})
                ],
            }
        )
        probe = GladosClient(self.config, transport=transport).probe_account()

        self.assertTrue(probe.cookie_valid)
        self.assertEqual(probe.active_base_url, "https://glados.rocks")
        self.assertEqual(probe.total_points_status, "not_requested")


if __name__ == "__main__":
    unittest.main()
