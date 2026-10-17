import unittest
from app import health_payload


class TestHealth(unittest.TestCase):
    def test_status_is_ok(self):
        result = health_payload()
        self.assertEqual(result["status"], "ok")

    def test_has_version_key(self):
        result = health_payload()
        self.assertIn("version", result)