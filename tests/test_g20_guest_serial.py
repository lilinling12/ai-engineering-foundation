"""Serial readiness requires exact per-run marker, not kernel logs or VMM API state."""
from pathlib import Path
import tempfile
import unittest
from foundation.g20_guest_serial import (
    MAX_SERIAL_BYTES, PREFIX, checked_boot_args, guest_marker_observed,
)

class GuestSerialTests(unittest.TestCase):
    def test_exact_nonce_marker_in_bounded_serial_output(self):
        nonce="a"*32
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"serial.log"
            path.write_bytes(b"Linux kernel booting\n" +
                             (PREFIX+" "+nonce+"\r\n").encode() + b"system up\n")
            self.assertTrue(guest_marker_observed(path,nonce))
            self.assertFalse(guest_marker_observed(path,"b"*32))
            self.assertIn("foundation.probe_token="+nonce,
                          checked_boot_args("console=ttyS0",nonce))

    def test_reject_truncated_spoofed_or_overlarge_log(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"serial.log"
            nonce="b"*32
            for text in (
                "garbage " + PREFIX + " " + nonce + "\n",
                PREFIX+" "+nonce+" extra\n",
                PREFIX+" "+nonce[:-1]+"\n",
                PREFIX+" "+nonce+"\x00\n",
            ):
                with self.subTest(text=repr(text)):
                    path.write_bytes(text.encode())
                    self.assertFalse(guest_marker_observed(path,nonce))
            path.write_bytes((PREFIX+" "+nonce+"\n").encode()+b"x"*MAX_SERIAL_BYTES)
            self.assertFalse(guest_marker_observed(path,nonce))

    def test_reject_symlink_malformed_challenge_and_relative_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            log=root/"serial"
            log.write_bytes((PREFIX+" "+("c"*32)+"\n").encode())
            link=root/"alias"
            link.symlink_to(log)
            self.assertFalse(guest_marker_observed(link,"c"*32))
            self.assertFalse(guest_marker_observed(log,"c"*31))
            self.assertFalse(guest_marker_observed(Path("serial.log"),"c"*32))
            with self.assertRaises(ValueError):
                checked_boot_args("root=/dev/vda","bad token")
