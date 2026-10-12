"""G1.9 unjailed Firecracker VMM diagnostics: mocked lifecycle, NEVER boot in CI."""
import hashlib
import os
from pathlib import Path
import socket
import stat
import tempfile
import unittest
from unittest.mock import Mock, patch

from foundation.g19_firecracker_smoke import (
    Assets, Trial, TrialDenied, OPERATOR_FLAG, OPERATOR_VALUE, BOOT_ARGS,
    run_probe, validate_assets, _clean_env, _stop_group, firecracker_api,
)
from foundation.g18_kvm_probe import KvmCapability

KVM_OK = KvmCapability("available", "kvm-api-version-confirmed", 12, True)

def sample_assets(root: Path):
    binary = root / "firecracker"
    kernel = root / "kernel.elf"
    rootfs = root / "rootfs.ext4"
    binary.write_bytes(b"\x7fELF" + b"\0" * 256)
    kernel.write_bytes(b"\x7fELF" + b"\0" * 256)
    img = bytearray(2048)
    img[1080:1082] = b"\x53\xef"
    rootfs.write_bytes(img)
    binary.chmod(0o700)
    return Assets(binary, kernel, rootfs, *(
        hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (binary, kernel, rootfs)
    ))

class G19FirecrackerTests(unittest.TestCase):
    def test_no_authorization_does_not_touch_kvm_or_files(self):
        with tempfile.TemporaryDirectory() as td:
            assets = sample_assets(Path(td))
            runtime = Mock(side_effect=AssertionError("must never run"))
            with patch.dict(os.environ, {}, clear=True):
                result = run_probe(assets, explicit=True, runner=runtime,
                                   capability=Mock(side_effect=AssertionError("no KVM probe")))
            self.assertEqual(result.reason, "operator-authorization-required")
            runtime.assert_not_called()

    def test_blocked_kvm_never_launches_firecracker(self):
        with tempfile.TemporaryDirectory() as td:
            assets = sample_assets(Path(td))
            runner = Mock(side_effect=AssertionError("no binary launch"))
            with patch.dict(os.environ, {OPERATOR_FLAG: OPERATOR_VALUE}):
                result = run_probe(assets, explicit=True, runner=runner,
                    capability=lambda: KvmCapability("blocked","kvm-permission-denied",None,True))
            self.assertEqual(result.reason, "kvm-host-unavailable")
            runner.assert_not_called()

    def test_asset_sha_symlink_and_writable_file_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            asset=sample_assets(root)
            validate_assets(asset)
            forged = Assets(asset.firecracker, asset.kernel, asset.rootfs,
                            "0"*64, asset.kernel_sha256, asset.rootfs_sha256)
            with self.assertRaises(TrialDenied):
                validate_assets(forged)
            alias=root/"alias"
            alias.symlink_to(asset.kernel)
            forged = Assets(asset.firecracker, alias, asset.rootfs,
                            asset.firecracker_sha256,asset.kernel_sha256,asset.rootfs_sha256)
            with self.assertRaises(TrialDenied):
                validate_assets(forged)
            asset.rootfs.chmod(0o666)
            with self.assertRaises(TrialDenied):
                validate_assets(asset)

    def test_clean_env_has_no_credentials_or_docker_sockets(self):
        with tempfile.TemporaryDirectory() as td:
            env = _clean_env(Path(td))
            self.assertEqual(set(env), {"PATH","HOME","LANG"})
            self.assertNotIn("DOCKER_HOST", env)
            self.assertNotIn("OPENAI_API_KEY", env)
            self.assertNotIn("GITHUB_TOKEN", env)

    def test_positive_vmm_lifecycle_is_not_guest_boot_proof(self):
        with tempfile.TemporaryDirectory() as td, \
             patch.dict(os.environ, {OPERATOR_FLAG: OPERATOR_VALUE}):
            assets = sample_assets(Path(td))
            proc = Mock()
            proc.poll.return_value = None
            proc.pid = 56789
            called=[]
            def fake_request(sock, method, resource, payload):
                self.assertTrue(sock.exists() or sock.parent.exists())
                called.append((method, resource, payload))
                return {"state":"Running"} if resource=="/" else None
            def fake_runner(argv, **kwargs):
                Path(argv[2]).touch()
                self.assertTrue(kwargs["start_new_session"])
                self.assertEqual(kwargs["env"].keys(), {"PATH","HOME","LANG"})
                return proc
            stopper=Mock(return_value=(True,True))
            with patch("foundation.g19_firecracker_smoke.Path.is_socket", return_value=True):
                state=run_probe(assets, explicit=True, runner=fake_runner,
                                request=fake_request, capability=lambda: KVM_OK,
                                stopper=stopper)
            self.assertEqual(state.status, "vmm-start-observed")
            self.assertFalse(state.guest_boot_verified)
            self.assertEqual([c[1] for c in called],
                             ["/machine-config", "/boot-source", "/drives/rootfs", "/actions", "/"])
            self.assertTrue(called[2][2]["is_read_only"])
            self.assertEqual(called[1][2]["boot_args"], BOOT_ARGS)
            self.assertFalse(any("network-interfaces" in c[1] for c in called))
            stopper.assert_called_once()

    def test_api_failure_still_attempts_cleanup(self):
        with tempfile.TemporaryDirectory() as td, \
             patch.dict(os.environ, {OPERATOR_FLAG: OPERATOR_VALUE}):
            assets=sample_assets(Path(td))
            proc=Mock()
            proc.poll.return_value=None
            proc.pid=56789
            def spawn(argv, **kwargs):
                Path(argv[2]).touch()
                return proc
            cleanup=Mock(return_value=(True,True))
            with patch("foundation.g19_firecracker_smoke.Path.is_socket",return_value=True):
                result=run_probe(assets, explicit=True, runner=spawn,
                                 request=Mock(side_effect=OSError("internal secret")),
                                 capability=lambda: KVM_OK,stopper=cleanup)
            self.assertEqual(result.status, "blocked")
            self.assertEqual(result.reason, "vmm-api-or-boot-error")
            cleanup.assert_called_once()

    def test_stop_group_handles_process_exit(self):
        proc=Mock()
        proc.pid=812345
        with patch("foundation.g19_firecracker_smoke.os.killpg",
                   side_effect=ProcessLookupError):
            signalled,reaped=_stop_group(proc)
        self.assertTrue(signalled)
        self.assertTrue(reaped)
        proc.wait.assert_called_once()

    def test_strict_guest_start_refuses_unverified_kernel_config(self):
        with tempfile.TemporaryDirectory() as td, \
             patch.dict(os.environ, {OPERATOR_FLAG: OPERATOR_VALUE}):
            assets = sample_assets(Path(td))
            runner = Mock(side_effect=AssertionError("should never spawn"))
            outcome = run_probe(assets, explicit=True, require_guest_ready=True,
                                capability=lambda: KVM_OK, runner=runner)
            self.assertEqual(outcome.reason, "kernel-config-required-for-guest-readiness")
            runner.assert_not_called()
            result=run_probe(assets, explicit=True, require_guest_ready=True,
                             capability=lambda:KVM_OK, runner=runner,
                             kernel_config=assets.kernel,
                             kernel_config_sha256=assets.kernel_sha256,
                             config_checker=Mock(side_effect=ValueError("no drivers")))
            self.assertEqual(result.reason, "kernel-config-compatibility-denied")
            runner.assert_not_called()

    def test_guest_readiness_mode_denies_missing_marker_even_if_vmm_running(self):
        with tempfile.TemporaryDirectory() as td, \
             patch.dict(os.environ, {OPERATOR_FLAG: OPERATOR_VALUE}):
            assets = sample_assets(Path(td))
            proc = Mock()
            proc.pid = 52732
            proc.poll.return_value = None
            def start(argv, **kwargs):
                Path(argv[2]).touch()
                self.assertNotEqual(kwargs["stdout"], __import__("subprocess").DEVNULL)
                return proc
            marker = Mock(return_value=False)
            with patch("foundation.g19_firecracker_smoke.Path.is_socket", return_value=True), \
                 patch("foundation.g19_firecracker_smoke.time.monotonic",
                       side_effect=[0.0, 0.0, 10.0]):
                outcome = run_probe(
                    assets, explicit=True, require_guest_ready=True,
                    runner=start,
                    request=lambda sock, method, path, payload: {"state":"Running"} if path=="/" else None,
                    capability=lambda: KVM_OK,
                    serial_checker=marker,
                    stopper=lambda _: (True,True),
                    kernel_config=assets.kernel,
                    kernel_config_sha256=assets.kernel_sha256,
                    config_checker=lambda *args: None,
                )
            self.assertEqual(outcome.status, "blocked")
            self.assertEqual(outcome.reason, "guest-readiness-marker-not-observed")
            self.assertFalse(outcome.guest_serial_ready_observed)

    def test_guest_marker_mode_requires_cleanup_and_never_claims_attestation(self):
        with tempfile.TemporaryDirectory() as td, \
             patch.dict(os.environ, {OPERATOR_FLAG: OPERATOR_VALUE}):
            assets = sample_assets(Path(td))
            proc=Mock()
            proc.poll.return_value=None
            proc.pid=52733
            observed=[]
            def start(argv, **kwargs):
                Path(argv[2]).touch()
                return proc
            def fake_api(sock, method, path, payload):
                if path == "/boot-source":
                    observed.append(payload["boot_args"])
                return {"state":"Running"} if path=="/" else None
            ready=Mock(return_value=True)
            with patch("foundation.g19_firecracker_smoke.Path.is_socket", return_value=True):
                result = run_probe(
                    assets, explicit=True, require_guest_ready=True,
                    runner=start, request=fake_api, capability=lambda:KVM_OK,
                    serial_checker=ready,stopper=lambda _:(True,True),
                    kernel_config=assets.kernel, kernel_config_sha256=assets.kernel_sha256,
                    config_checker=lambda *args: None,
                )
            self.assertEqual(result.status,"guest-marker-observed")
            self.assertTrue(result.kernel_config_preflight_passed)
            self.assertTrue(result.guest_serial_ready_observed)
            self.assertFalse(result.guest_boot_verified)
            self.assertIn("foundation.probe_token=",observed[0])
            self.assertEqual(len(ready.call_args.args[1]),32)

    def test_unverified_cleanup_blocks_even_with_guest_marker(self):
        with tempfile.TemporaryDirectory() as td, \
             patch.dict(os.environ, {OPERATOR_FLAG: OPERATOR_VALUE}):
            assets = sample_assets(Path(td))
            proc=Mock()
            proc.poll.return_value=None
            proc.pid=52734
            def start(argv, **kwargs):
                Path(argv[2]).touch()
                return proc
            with patch("foundation.g19_firecracker_smoke.Path.is_socket", return_value=True):
                outcome=run_probe(
                    assets, explicit=True, require_guest_ready=True,
                    runner=start, request=lambda sock,m,p,pl: {"state":"Running"} if p=="/" else None,
                    capability=lambda:KVM_OK, serial_checker=lambda path,nonce:True,
                    stopper=lambda _: (False,True),
                    kernel_config=assets.kernel, kernel_config_sha256=assets.kernel_sha256,
                    config_checker=lambda *args: None,
                )
            self.assertEqual(outcome.status,"blocked")
            self.assertEqual(outcome.reason,"cleanup-unverified")

    def test_firecracker_api_rejects_nonreviewed_actions(self):
        with self.assertRaises(TrialDenied):
            firecracker_api(Path("/tmp/socket"),"PUT","/network-interfaces/net1",{})
