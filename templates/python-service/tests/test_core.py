import unittest
from app.core import health

class HealthTests(unittest.TestCase):
    def test_health(self):
        self.assertEqual(health(), {"status": "ok"})
