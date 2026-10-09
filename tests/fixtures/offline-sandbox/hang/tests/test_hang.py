import time
import unittest

class HangingCheck(unittest.TestCase):
    def test_run_timeout(self):
        time.sleep(25)
