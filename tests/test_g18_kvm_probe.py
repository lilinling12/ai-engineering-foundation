"""Host KVM preflight reports actual kernel API, not environment-marker claims."""
import errno
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import Mock, patch

from foundation.g18_kvm_probe import (
    EXPECTED_KVM_API_VERSION, KVM_DEVICE, KVM_GET_API_VERSION,
    KvmCapability, probe_kvm, write_preflight,
)

CHAR = os.stat_result((stat.S_IFCHR | 0o660,) + (0,) * 9)
REGULAR = os.stat_result((stat.S_IFREG | 0o600,) + (0,) * 9)

class KvmHostProbeTests(unittest.TestCase):
    def test_does_not_accept_host_env_flags_as_identity(self):
        with patch.dict(os.environ, {"FOUNDATION_EPHEMERAL_RUNNER": "yes",
                                     "KVM_AVAILABLE": "true"}, clear=False):
            result = probe_kvm(system="Linux",
                               lstat_device=Mock(side_effect=FileNotFoundError),
                               open_device=Mock(side_effect=AssertionError("cannot open")))
        self.assertEqual(result.result, "blocked")
        self.assertEqual(result.reason, "kvm-device-missing")

    def test_supported_linux_kernel_ioctl_is_required(self):
        opened = Mock(return_value=75)
        query = Mock(return_value=EXPECTED_KVM_API_VERSION)
        closed = Mock()
        probe = probe_kvm(system="Linux", lstat_device=Mock(return_value=CHAR),
                          open_device=opened, fstat_device=Mock(return_value=CHAR),
                          ioctl=query, close_device=closed)
        self.assertEqual(probe, KvmCapability("available", "kvm-api-version-confirmed", 12, True))
        self.assertEqual(opened.call_args.args[0], KVM_DEVICE)
        self.assertTrue(opened.call_args.args[1] & os.O_RDWR)
        self.assertEqual(query.call_args.args, (75, KVM_GET_API_VERSION, 0))
        closed.assert_called_once_with(75)

    def test_refuse_symlink_regular_file_and_other_os(self):
        open_mock = Mock(side_effect=AssertionError("should not open"))
        other_os = probe_kvm(system="Darwin", lstat_device=Mock(side_effect=AssertionError("no stat")))
        self.assertEqual(other_os.reason, "unsupported-operating-system")
        regular = probe_kvm(system="Linux", lstat_device=Mock(return_value=REGULAR),
                            open_device=open_mock)
        self.assertEqual(regular.reason, "kvm-not-character-device")
        open_mock.assert_not_called()

    def test_permission_denied_has_no_open_fd(self):
        close = Mock()
        denied = probe_kvm(
            system="Linux", lstat_device=Mock(return_value=CHAR),
            open_device=Mock(side_effect=PermissionError(errno.EACCES, "denied")),
            close_device=close,
        )
        self.assertEqual(denied.reason, "kvm-permission-denied")
        close.assert_not_called()

    def test_ioctl_error_and_bad_version_fail_closed_and_close_fd(self):
        for response in (OSError(errno.ENOTTY, "not KVM"), 10, b"12"):
            with self.subTest(response=repr(response)):
                query = Mock(side_effect=response) if isinstance(response, OSError) else Mock(return_value=response)
                close = Mock()
                outcome = probe_kvm(system="Linux", lstat_device=Mock(return_value=CHAR),
                                    open_device=Mock(return_value=5),
                                    fstat_device=Mock(return_value=CHAR),
                                    ioctl=query, close_device=close)
                self.assertEqual(outcome.result, "blocked")
                close.assert_called_once_with(5)

    def test_written_evidence_cannot_claim_vm_execution(self):
        with tempfile.TemporaryDirectory() as td, \
             patch("foundation.g18_kvm_probe.ROOT", Path(td)), \
             patch("foundation.g18_kvm_probe.probe_kvm",
                   return_value=KvmCapability("available", "kvm-api-version-confirmed", 12, True)):
            output = write_preflight()
            record = json.loads(output.read_text(encoding="utf-8"))
            self.assertFalse(record["microVmStarted"])
            self.assertFalse(record["vmAdmissionAllowed"])
            self.assertFalse(record["inferenceCredentialsUsed"])
            self.assertEqual(record["kvm"]["result"], "available")
            self.assertEqual(record["assessment"], "capability-probe-only-NOT-VM-isolation")
