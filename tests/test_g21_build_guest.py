"""G2.1 build contract tests; actual compiler/ext4 execution in dedicated CI job."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from foundation.g21_build_guest import (
    GuestBuildError, TEST_NONCE, TEST_MARKER, _invoke, build_guest,
)

class SyntheticGuestBuildTests(unittest.TestCase):
    def test_output_must_be_a_new_absolute_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            with self.assertRaises(GuestBuildError):
                build_guest(Path("relative"))
            existing = p / "existing"
            existing.mkdir()
            with self.assertRaises(GuestBuildError):
                build_guest(existing)
            symlink = p / "alias"
            symlink.symlink_to(p / "new")
            with self.assertRaises(GuestBuildError):
                build_guest(symlink)

    def test_wire_line_matches_g20_readiness(self):
        self.assertEqual(len(TEST_NONCE), 32)
        self.assertEqual(TEST_MARKER,
                         ("FOUNDATION_GUEST_READY_V1 " + TEST_NONCE + "\n").encode())

    def test_build_invocation_uses_no_shell_and_minimal_env(self):
        with patch("foundation.g21_build_guest.subprocess.run") as run:
            run.return_value.returncode = 0
            _invoke(["readelf", "-l", "/tmp/fixture"])
            self.assertEqual(run.call_args.args[0][0], "readelf")
            self.assertFalse(run.call_args.kwargs.get("shell", False))
            self.assertEqual(set(run.call_args.kwargs["env"]),
                             {"HOME", "PATH", "LANG"})
            self.assertEqual(run.call_args.kwargs["stderr"], __import__("subprocess").DEVNULL)

    def test_guest_init_requires_guest_pid1_except_self_test(self):
        source = (Path(__file__).resolve().parent.parent /
                  "guest" / "synthetic-init.c").read_text(encoding="utf-8")
        self.assertIn("getpid() != 1", source)
        self.assertIn('strcmp(argv[1], "--self-test")', source)
        self.assertIn('foundation.probe_token=', source)
        self.assertIn('FOUNDATION_GUEST_READY_V1', source)
        self.assertNotIn("execve(", source)
