import os
from pathlib import Path
import socket
import unittest

class PolicyProof(unittest.TestCase):
    def test_nonroot(self):
        self.assertEqual(os.geteuid(), 65534)

    def test_rootfs_readonly(self):
        with self.assertRaises(OSError):
            Path("/foundation-should-not-write").write_text("deny")

    def test_external_network_denied(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.5)
            with self.assertRaises(OSError):
                sock.connect(("1.1.1.1", 443))
