import tempfile
from pathlib import Path
import unittest
from foundation.sandbox import SandboxPolicy, SandboxPolicyError, plan_docker_run, command_catalog
from foundation.provider_contract import ProviderRequest, ProviderRequestError, ProviderCapability, planned_provider_flow

DIGEST = "python@sha256:" + "a" * 64

class SandboxTests(unittest.TestCase):
    def test_offline_nonprivileged_policy(self):
        with tempfile.TemporaryDirectory() as path:
            argv = plan_docker_run(Path(path), "python-unit", SandboxPolicy(DIGEST))
            self.assertIn("--network=none", argv)
            self.assertIn("--cap-drop=ALL", argv)
            self.assertIn("--read-only", argv)
            self.assertIn("--pull=never", argv)
            self.assertIn("--security-opt=no-new-privileges", argv)
            self.assertIn("type=bind,src=", " ".join(argv))
            self.assertEqual(argv[-len(("python", "-B", "-m", "unittest", "discover", "-s", "tests", "-v")):],
                             ("python", "-B", "-m", "unittest", "discover", "-s", "tests", "-v"))

    def test_never_run_arbitrary_command(self):
        with tempfile.TemporaryDirectory() as path:
            for command in ("bash", "curl", "../../escape"):
                with self.subTest(command=command), self.assertRaises(SandboxPolicyError):
                    plan_docker_run(Path(path), command, SandboxPolicy(DIGEST))

    def test_reject_tag_unpinned_and_network(self):
        with tempfile.TemporaryDirectory() as path:
            for image in ("python:3.12", "latest", "python@sha256:abc"):
                with self.subTest(image=image), self.assertRaises(SandboxPolicyError):
                    plan_docker_run(Path(path), "python-unit", SandboxPolicy(image))
            with self.assertRaises(SandboxPolicyError):
                plan_docker_run(Path(path), "python-unit", SandboxPolicy(DIGEST, network="bridge"))

    def test_reject_resource_escalation(self):
        with tempfile.TemporaryDirectory() as path:
            with self.assertRaises(SandboxPolicyError):
                plan_docker_run(Path(path), "python-unit", SandboxPolicy(DIGEST, memory_mb=8192))
            with self.assertRaises(SandboxPolicyError):
                plan_docker_run(Path(path), "python-unit", SandboxPolicy(DIGEST, timeout_seconds=1000))

    def test_reject_relative_workspace(self):
        with self.assertRaises(SandboxPolicyError):
            plan_docker_run(Path("."), "python-unit", SandboxPolicy(DIGEST))

    def test_catalog_does_not_include_shell(self):
        self.assertEqual(command_catalog(), ("python-eval", "python-unit"))

    def test_provider_has_no_live_executor(self):
        p = ProviderRequest("ticket-1", "a"*64, "codex",
                            frozenset({ProviderCapability.READ_AUTHORITY, ProviderCapability.PROPOSE_PATCH}))
        self.assertEqual(planned_provider_flow(p)[-1], "handoff")
        with self.assertRaises(ProviderRequestError):
            planned_provider_flow(ProviderRequest("ticket-1", "a"*64, "unknown", frozenset()))
        with self.assertRaises(ProviderRequestError):
            planned_provider_flow(ProviderRequest("ticket-1", "a"*64, "claude-code", frozenset(), max_steps=900))

if __name__ == "__main__":
    unittest.main()
